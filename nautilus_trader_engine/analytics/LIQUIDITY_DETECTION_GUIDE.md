# Liquidity Detection System Guide

## Overview

The Liquidity Detection System is a sophisticated, real-time liquidity analysis framework designed for institutional trading environments. It provides advanced hidden liquidity identification, iceberg order detection, dark pool activity estimation, and liquidity scoring capabilities with machine learning-enhanced detection algorithms.

## Key Features

### 🔍 **Hidden Liquidity Identification**
- **Algorithmic Detection**: Advanced algorithms to identify hidden liquidity in order books
- **Pattern Recognition**: ML-based pattern recognition for concealed orders
- **Cross-Venue Analysis**: Multi-exchange hidden liquidity detection
- **Real-Time Monitoring**: Continuous monitoring of liquidity availability

### 🧊 **Iceberg Order Detection**
- **Volume Analysis**: Statistical analysis of order execution patterns
- **Size Clustering**: Detection of repeated order sizes indicating icebergs
- **Timing Analysis**: Analysis of order placement and execution timing
- **Confidence Scoring**: Probabilistic scoring of iceberg order likelihood

### 🌊 **Dark Pool Activity Estimation**
- **Volume Reconciliation**: Comparison of lit vs total volume
- **Price Impact Analysis**: Analysis of price movements without visible volume
- **Cross-Reference Analysis**: Multi-source data correlation
- **Activity Scoring**: Quantitative dark pool activity measurement

### 📊 **Liquidity Score Calculation**
- **Multi-Factor Scoring**: Comprehensive liquidity assessment
- **Venue-Specific Metrics**: Individual venue liquidity scoring
- **Time-Based Analysis**: Intraday liquidity pattern analysis
- **Predictive Modeling**: Forward-looking liquidity availability prediction
## Ar
chitecture

```
┌─────────────────────────────────────────────────────────────┐
│                Liquidity Detection System                    │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Hidden    │  │   Iceberg   │  │  Dark Pool  │        │
│  │ Liquidity   │  │   Order     │  │  Activity   │        │
│  │ Detection   │  │ Detection   │  │ Estimation  │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ Liquidity   │  │   Pattern   │  │   Volume    │        │
│  │  Scoring    │  │Recognition  │  │  Analysis   │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │    ML       │  │ Real-Time   │  │ Historical  │        │
│  │  Models     │  │ Processing  │  │  Analysis   │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### LiquidityDetectionEngine Class

```python
class LiquidityDetectionEngine:
    def __init__(self, config: LiquidityDetectionConfig):
        self.config = config
        self.hidden_liquidity_detector = HiddenLiquidityDetector()
        self.iceberg_detector = IcebergOrderDetector()
        self.dark_pool_estimator = DarkPoolEstimator()
        self.liquidity_scorer = LiquidityScorer()
        self.pattern_recognizer = PatternRecognizer()
```

### Data Structures

```python
@dataclass
class HiddenLiquiditySignal:
    symbol: str
    timestamp: datetime
    price_level: float
    estimated_size: float
    confidence: float
    detection_method: str
    venue: Optional[str] = None
    
@dataclass
class IcebergOrderDetection:
    symbol: str
    timestamp: datetime
    side: str  # 'buy' or 'sell'
    estimated_total_size: float
    visible_size: float
    execution_pattern: Dict[str, Any]
    confidence: float
    
@dataclass
class LiquidityScore:
    symbol: str
    timestamp: datetime
    overall_score: float  # 0-100
    visible_liquidity: float
    hidden_liquidity: float
    dark_pool_activity: float
    venue_scores: Dict[str, float]
    time_to_liquidity: Optional[float] = None
```## 
Usage Examples

### Basic Liquidity Detection

```python
import asyncio
from nautilus_trader_engine.analytics import LiquidityDetectionEngine, LiquidityDetectionConfig

async def basic_liquidity_detection():
    # Initialize liquidity detection engine
    config = LiquidityDetectionConfig(
        enable_hidden_liquidity_detection=True,
        enable_iceberg_detection=True,
        enable_dark_pool_estimation=True,
        confidence_threshold=0.7
    )
    
    liquidity_engine = LiquidityDetectionEngine(config)
    await liquidity_engine.start()
    
    # Analyze liquidity for a symbol
    symbol = "AAPL"
    
    # Detect hidden liquidity
    hidden_liquidity = await liquidity_engine.detect_hidden_liquidity(
        symbol=symbol,
        lookback_minutes=30,
        price_range_bps=25  # Within 25 bps of current price
    )
    
    print(f"{symbol} Hidden Liquidity Analysis:")
    for signal in hidden_liquidity:
        print(f"  Price: ${signal.price_level:.2f}")
        print(f"  Estimated Size: {signal.estimated_size:,.0f}")
        print(f"  Confidence: {signal.confidence:.3f}")
        print(f"  Method: {signal.detection_method}")
        print(f"  Venue: {signal.venue}")
    
    # Detect iceberg orders
    iceberg_orders = await liquidity_engine.detect_iceberg_orders(
        symbol=symbol,
        min_execution_count=5,
        size_consistency_threshold=0.8
    )
    
    print(f"\\nIceberg Order Detection:")
    for iceberg in iceberg_orders:
        print(f"  Side: {iceberg.side}")
        print(f"  Estimated Total: {iceberg.estimated_total_size:,.0f}")
        print(f"  Visible Size: {iceberg.visible_size:,.0f}")
        print(f"  Confidence: {iceberg.confidence:.3f}")
        print(f"  Pattern: {iceberg.execution_pattern}")
    
    # Estimate dark pool activity
    dark_pool_activity = await liquidity_engine.estimate_dark_pool_activity(
        symbol=symbol,
        timeframe="1h"
    )
    
    print(f"\\nDark Pool Activity Estimation:")
    print(f"  Estimated Dark Volume: {dark_pool_activity.estimated_volume:,.0f}")
    print(f"  Dark Pool Percentage: {dark_pool_activity.dark_percentage:.1%}")
    print(f"  Activity Score: {dark_pool_activity.activity_score:.3f}")
    print(f"  Confidence: {dark_pool_activity.confidence:.3f}")
    
    # Calculate comprehensive liquidity score
    liquidity_score = await liquidity_engine.calculate_liquidity_score(
        symbol=symbol,
        include_predictions=True
    )
    
    print(f"\\nLiquidity Score:")
    print(f"  Overall Score: {liquidity_score.overall_score:.1f}/100")
    print(f"  Visible Liquidity: {liquidity_score.visible_liquidity:.1f}")
    print(f"  Hidden Liquidity: {liquidity_score.hidden_liquidity:.1f}")
    print(f"  Dark Pool Activity: {liquidity_score.dark_pool_activity:.1f}")
    print(f"  Time to Liquidity: {liquidity_score.time_to_liquidity:.1f}s")
    
    await liquidity_engine.stop()

# Run the example
asyncio.run(basic_liquidity_detection())
```