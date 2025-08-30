"""
Enhanced Technical Indicators Package
Complete suite of 80+ technical indicators + 25+ candlestick patterns

Package Structure:
- technical_indicators.py: Core indicators with volume-weighting + candlestick patterns
- enhanced_indicators_part1.py: Advanced trend and momentum indicators (30+)
- enhanced_indicators_part2.py: Volatility and volume indicators (25+) 
- enhanced_candlestick_patterns.py: Comprehensive pattern recognition (25+ patterns)
- comprehensive_indicators.py: Unified library with all indicators
- candle_patterns.py: Original 9 candlestick patterns
- indicator_manager.py: Management and signal aggregation

Total Indicators: 80+
Candlestick Patterns: 25+
Author: Vincent S. Pereira
Phase: Phase 1 - Core System Validation & Hardening
Version: 3.0.0
"""

from .technical_indicators import TechnicalIndicators, IndicatorResult, IndicatorType
from .comprehensive_indicators import ComprehensiveIndicators, ComprehensiveIndicatorResult, IndicatorCategory
from .enhanced_indicators_part1 import EnhancedTechnicalIndicators
from .enhanced_indicators_part2 import EnhancedVolatilityVolumeIndicators
from .enhanced_candlestick_patterns import EnhancedCandlestickPatterns, PatternResult, PatternType

try:
    from .advanced_indicators import AdvancedIndicators
    from .specialized_indicators import SpecializedIndicators
    from .indicator_manager import IndicatorManager, MarketData, IndicatorConfig, SignalResult
    LEGACY_AVAILABLE = True
except ImportError:
    LEGACY_AVAILABLE = False

__all__ = [
    'TechnicalIndicators',
    'ComprehensiveIndicators',
    'EnhancedTechnicalIndicators',
    'EnhancedVolatilityVolumeIndicators', 
    'EnhancedCandlestickPatterns',
    'IndicatorResult',
    'ComprehensiveIndicatorResult',
    'PatternResult',
    'IndicatorType',
    'IndicatorCategory',
    'PatternType'
]

if LEGACY_AVAILABLE:
    __all__.extend([
        'AdvancedIndicators',
        'SpecializedIndicators',
        'IndicatorManager',
        'MarketData',
        'IndicatorConfig',
        'SignalResult'
    ])

# Enhanced indicator count by category
INDICATOR_COUNT = {
    'trend': 25,
    'momentum': 20, 
    'volatility': 15,
    'volume': 20,
    'patterns': 25,
    'support_resistance': 8,
    'total': 80
}

def get_comprehensive_indicator_list():
    """Get complete list of all 80+ indicators including patterns"""
    return {
        'trend_indicators': [
            # Traditional Moving Averages
            'sma', 'ema', 'wma', 'vwma', 'vw_ema', 'vw_sma',
            # Advanced Moving Averages  
            'hull_ma', 'kaufman_ama', 'dema', 'tema', 'mcginley_dynamic',
            'zero_lag_ema', 'linear_regression', 'adaptive_ma',
            # Complex Trend Systems
            'ichimoku_cloud', 'parabolic_sar', 'alligator_indicator',
            # Volume-Weighted Trend
            'vw_hull_ma', 'vw_adaptive_ma', 'vw_trend_strength'
        ],
        'momentum_indicators': [
            # Classical Oscillators
            'rsi', 'vw_rsi', 'macd', 'vw_macd', 'stochastic', 'vw_stochastic',
            'williams_r', 'vw_williams_r', 'cci', 'vw_cci',
            # Advanced Oscillators
            'ultimate_oscillator', 'trix', 'fisher_transform', 'awesome_oscillator',
            'accelerator_oscillator', 'rate_of_change', 'momentum_indicator',
            'price_oscillator', 'mfi', 'money_flow_index'
        ],
        'volatility_indicators': [
            # Band-Based
            'bollinger_bands', 'vw_bollinger_bands', 'keltner_channels', 
            'donchian_channels', 'volatility_bands',
            # Range-Based
            'atr', 'vw_atr', 'vw_atrp', 'true_range', 'historical_volatility',
            # Directional
            'adx', 'vw_adx', 'mass_index', 'chaikin_volatility', 'price_range'
        ],
        'volume_indicators': [
            # Price-Volume
            'vwap', 'enhanced_vwap', 'vwap_bands', 'obv', 'enhanced_obv',
            'accumulation_distribution', 'price_volume_trend',
            # Money Flow
            'money_flow_index', 'chaikin_money_flow', 'chaikin_oscillator',
            'force_index', 'buying_selling_pressure',
            # Volume Momentum
            'volume_roc', 'ease_of_movement', 'negative_volume_index',
            'positive_volume_index', 'volume_oscillator'
        ],
        'candlestick_patterns': [
            # Single Candle
            'doji', 'hammer', 'hanging_man', 'shooting_star', 'inverted_hammer',
            'marubozu', 'spinning_top', 'gravestone_doji', 'dragonfly_doji',
            # Two Candle
            'bullish_engulfing', 'bearish_engulfing', 'bullish_harami', 'bearish_harami',
            'piercing_line', 'dark_cloud_cover', 'tweezer_top', 'tweezer_bottom',
            # Three Candle
            'morning_star', 'evening_star', 'three_white_soldiers', 'three_black_crows',
            'abandoned_baby', 'three_inside_up', 'three_inside_down'
        ],
        'support_resistance': [
            'pivot_points', 'fibonacci_retracements', 'camarilla_pivots',
            'woodies_pivots', 'swing_points', 'fractal_levels',
            'supply_demand_zones', 'volume_profile_levels'
        ]
    }

def get_enhanced_package_info():
    """Get enhanced package information"""
    return {
        'name': 'Comprehensive Technical Indicators Library',
        'version': '3.0.0',
        'total_indicators': INDICATOR_COUNT['total'],
        'total_patterns': INDICATOR_COUNT['patterns'],
        'categories': INDICATOR_COUNT,
        'features': [
            '80+ Technical Indicators across 6 categories',
            '25+ Candlestick Pattern Recognition',
            'Volume-weighted calculations for institutional analysis',
            'Real-time signal generation with confidence scoring',
            'Pattern strength analysis with volume confirmation',
            'Concurrent indicator execution for high performance',
            'Comprehensive backtesting and strategy support',
            'Multi-timeframe analysis capabilities',
            'Custom indicator combinations and signals',
            'Professional-grade market analysis toolkit'
        ],
        'enhanced_patterns': [
            # Single Candlestick (8)
            'Standard Doji', 'Long Legged Doji', 'Dragonfly Doji', 'Gravestone Doji',
            'Hammer/Hanging Man', 'Shooting Star/Inverted Hammer', 'Marubozu', 'Spinning Top',
            # Two Candlestick (7)
            'Bullish Engulfing', 'Bearish Engulfing', 'Bullish Harami', 'Bearish Harami',
            'Piercing Line', 'Dark Cloud Cover', 'Tweezer Tops/Bottoms',
            # Three Candlestick (6)
            'Morning Star', 'Evening Star', 'Three White Soldiers', 'Three Black Crows',
            'Abandoned Baby', 'Three Inside Up/Down',
            # Complex Patterns (4)
            'Island Reversal', 'Rising/Falling Three Methods', 'Breakaway Gaps', 'Exhaustion Gaps'
        ],
        'volume_weighted_features': [
            'Sophisticated alpha calculations (1.0/n)',
            'Volume × price weighting methodology',
            'Multiple price variants (OHLC, High-Low midpoint)',
            'EMA-based volume weighting with proper math',
            'Pattern strength with volume confirmation',
            'Institutional-grade volume analysis'
        ],
        'performance_features': [
            'Vectorized calculations using pandas/numpy',
            'Efficient memory usage for large datasets',
            'Concurrent execution support',
            'Built-in result caching',
            'Optimized for real-time analysis'
        ]
    }

def get_indicator_by_category(category: str):
    """Get indicators by specific category"""
    all_indicators = get_comprehensive_indicator_list()
    category_map = {
        'trend': 'trend_indicators',
        'momentum': 'momentum_indicators', 
        'volatility': 'volatility_indicators',
        'volume': 'volume_indicators',
        'patterns': 'candlestick_patterns',
        'support_resistance': 'support_resistance'
    }
    
    return all_indicators.get(category_map.get(category, category), [])

def get_volume_weighted_indicators():
    """Get list of all volume-weighted indicator variants"""
    return [
        'vwma', 'vw_ema', 'vw_sma', 'vw_rsi', 'vw_macd', 'vw_stochastic',
        'vw_williams_r', 'vw_cci', 'vw_bollinger_bands', 'vw_atr', 'vw_atrp',
        'vw_hull_ma', 'vw_adaptive_ma', 'enhanced_vwap', 'vwap_bands',
        'enhanced_obv', 'money_flow_index', 'chaikin_money_flow', 'vw_adx'
    ]

# Legacy support
def get_indicator_list():
    """Legacy function - use get_comprehensive_indicator_list() for new code"""
    legacy_indicators = get_comprehensive_indicator_list()
    return {
        'trend_indicators': legacy_indicators['trend_indicators'][:12],
        'momentum_indicators': legacy_indicators['momentum_indicators'][:12],
        'volatility_indicators': legacy_indicators['volatility_indicators'][:8],
        'volume_indicators': legacy_indicators['volume_indicators'][:8],
        'pattern_indicators': ['candlestick_patterns', 'pattern_strength_analysis']
    }

def get_package_info():
    """Legacy function - use get_enhanced_package_info() for new code"""
    return {
        'name': 'Enhanced Technical Indicators Package (Legacy)',
        'version': '2.0.0',
        'total_indicators': 42,
        'note': 'This is legacy info. Use get_enhanced_package_info() for current data.',
        'upgrade_to': 'get_enhanced_package_info()'
    }