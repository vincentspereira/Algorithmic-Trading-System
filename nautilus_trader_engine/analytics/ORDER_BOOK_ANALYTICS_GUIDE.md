# Order Book Analytics Guide

## Overview

The Order Book Analytics Engine is a comprehensive, real-time order book analysis system designed for institutional trading environments. It provides sophisticated bid-ask spread analysis, market depth calculation, order book imbalance detection, and price level clustering analysis with sub-millisecond processing capabilities.

## Key Features

### 📊 **Real-Time Bid-Ask Spread Analysis**
- **Spread Monitoring**: Continuous bid-ask spread tracking and analysis
- **Spread Decomposition**: Adverse selection, inventory, and processing cost components
- **Cross-Venue Analysis**: Multi-exchange spread comparison and arbitrage detection
- **Historical Spread Patterns**: Time-of-day and volatility-based spread analysis

### 📈 **Market Depth Calculation**
- **Depth Visualization**: Real-time order book depth charts and heatmaps
- **Liquidity Metrics**: Available liquidity at various price levels
- **Depth Imbalance**: Buy vs sell side liquidity analysis
- **Market Impact Estimation**: Price impact prediction for various order sizes

### ⚖️ **Order Book Imbalance Detection**
- **Real-Time Imbalance Scoring**: Continuous imbalance measurement and scoring
- **Predictive Analytics**: Short-term price movement prediction based on imbalances
- **Imbalance Alerts**: Automated alerts for significant imbalance conditions
- **Historical Imbalance Analysis**: Pattern recognition in historical imbalance data

### 🎯 **Price Level Clustering Analysis**
- **Support/Resistance Identification**: Algorithmic support and resistance level detection
- **Order Clustering**: Large order concentration analysis
- **Psychological Levels**: Round number and technical level identification
- **Dynamic Level Updates**: Real-time adjustment of key price levels

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                Order Book Analytics Engine                   │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Spread    │  │   Market    │  │  Imbalance  │        │
│  │  Analysis   │  │   Depth     │  │  Detection  │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Price     │  │ Liquidity   │  │   Market    │        │
│  │ Clustering  │  │  Analysis   │  │   Impact    │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ Real-Time   │  │ Historical  │  │   Alert     │        │
│  │ Processing  │  │  Analysis   │  │  System     │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### OrderBookAnalytics Class

Main orchestrator for order book analysis:

```python
class OrderBookAnalytics:
    def __init__(self, config: OrderBookConfig):
        self.config = config
        self.spread_analyzer = SpreadAnalyzer()
        self.depth_calculator = DepthCalculator()
        self.imbalance_detector = ImbalanceDetector()
        self.clustering_analyzer = ClusteringAnalyzer()
        self.liquidity_analyzer = LiquidityAnalyzer()
```

### Order Book Data Structures

```python
@dataclass
class OrderBookLevel:
    price: float
    size: float
    order_count: int
    timestamp: datetime

@dataclass
class OrderBookSnapshot:
    symbol: str
    timestamp: datetime
    bids: List[OrderBookLevel]
    asks: List[OrderBookLevel]
    sequence_number: int
    
    @property
    def best_bid(self) -> float:
        return self.bids[0].price if self.bids else 0.0
    
    @property
    def best_ask(self) -> float:
        return self.asks[0].price if self.asks else float('inf')
    
    @property
    def spread(self) -> float:
        return self.best_ask - self.best_bid
    
    @property
    def mid_price(self) -> float:
        return (self.best_bid + self.best_ask) / 2

@dataclass
class SpreadAnalysis:
    symbol: str
    timestamp: datetime
    spread: float
    spread_bps: float  # Basis points
    relative_spread: float  # Spread / mid price
    adverse_selection_component: float
    inventory_component: float
    processing_component: float
    
@dataclass
class ImbalanceMetrics:
    symbol: str
    timestamp: datetime
    imbalance_ratio: float  # -1 to 1
    bid_volume: float
    ask_volume: float
    weighted_imbalance: float
    depth_imbalance: float
    predicted_direction: str  # 'up', 'down', 'neutral'
    confidence: float
```

## Usage Examples

### Basic Order Book Analysis

```python
import asyncio
from nautilus_trader_engine.analytics import OrderBookAnalytics, OrderBookConfig

async def basic_order_book_analysis():
    # Initialize order book analytics
    config = OrderBookConfig(
        enable_spread_analysis=True,
        enable_depth_calculation=True,
        enable_imbalance_detection=True,
        enable_clustering_analysis=True,
        update_frequency_ms=100
    )
    
    analytics = OrderBookAnalytics(config)
    await analytics.start()
    
    # Analyze order book for a symbol
    symbol = "AAPL"
    
    # Get current order book snapshot
    order_book = await get_order_book_snapshot(symbol)
    
    # Perform spread analysis
    spread_analysis = await analytics.analyze_spread(order_book)
    
    print(f"{symbol} Spread Analysis:")
    print(f"  Spread: ${spread_analysis.spread:.4f}")
    print(f"  Spread (bps): {spread_analysis.spread_bps:.2f}")
    print(f"  Relative Spread: {spread_analysis.relative_spread:.4f}")
    print(f"  Components:")
    print(f"    Adverse Selection: {spread_analysis.adverse_selection_component:.4f}")
    print(f"    Inventory: {spread_analysis.inventory_component:.4f}")
    print(f"    Processing: {spread_analysis.processing_component:.4f}")
    
    # Calculate market depth
    depth_analysis = await analytics.calculate_depth(
        order_book=order_book,
        depth_levels=[100, 500, 1000, 5000]  # Share quantities
    )
    
    print(f"\\nMarket Depth Analysis:")
    for level, depth in depth_analysis.depth_levels.items():
        print(f"  {level} shares:")
        print(f"    Bid Impact: {depth.bid_impact:.4f}")
        print(f"    Ask Impact: {depth.ask_impact:.4f}")
        print(f"    Available Liquidity: ${depth.available_liquidity:,.2f}")
    
    # Detect order book imbalance
    imbalance = await analytics.detect_imbalance(order_book)
    
    print(f"\\nOrder Book Imbalance:")
    print(f"  Imbalance Ratio: {imbalance.imbalance_ratio:.3f}")
    print(f"  Bid Volume: {imbalance.bid_volume:,.0f}")
    print(f"  Ask Volume: {imbalance.ask_volume:,.0f}")
    print(f"  Weighted Imbalance: {imbalance.weighted_imbalance:.3f}")
    print(f"  Predicted Direction: {imbalance.predicted_direction}")
    print(f"  Confidence: {imbalance.confidence:.3f}")
    
    # Analyze price level clustering
    clustering = await analytics.analyze_clustering(
        order_book=order_book,
        lookback_periods=20
    )
    
    print(f"\\nPrice Level Clustering:")
    print(f"  Support Levels: {[f'${level:.2f}' for level in clustering.support_levels]}")
    print(f"  Resistance Levels: {[f'${level:.2f}' for level in clustering.resistance_levels]}")
    print(f"  Cluster Strength: {clustering.cluster_strength:.3f}")
    
    await analytics.stop()

# Run the example
asyncio.run(basic_order_book_analysis())
```

### Real-Time Order Book Monitoring

```python
async def real_time_order_book_monitoring():
    analytics = OrderBookAnalytics(OrderBookConfig(
        real_time_mode=True,
        update_frequency_ms=50,  # 50ms updates
        enable_alerts=True
    ))
    
    await analytics.start()
    
    # Set up real-time callbacks
    async def spread_callback(spread_event):
        spread = spread_event.spread_analysis
        
        if spread.spread_bps > 20:  # Wide spread alert
            print(f"🔴 WIDE SPREAD ALERT: {spread_event.symbol}")
            print(f"   Spread: {spread.spread_bps:.2f} bps")
            print(f"   Time: {spread.timestamp}")
    
    async def imbalance_callback(imbalance_event):
        imbalance = imbalance_event.imbalance
        
        if abs(imbalance.imbalance_ratio) > 0.7:  # Strong imbalance
            direction = "📈 BUY" if imbalance.imbalance_ratio > 0 else "📉 SELL"
            print(f"{direction} IMBALANCE: {imbalance_event.symbol}")
            print(f"   Ratio: {imbalance.imbalance_ratio:.3f}")
            print(f"   Confidence: {imbalance.confidence:.3f}")
            print(f"   Predicted: {imbalance.predicted_direction}")
    
    async def depth_callback(depth_event):
        depth = depth_event.depth_analysis
        
        # Alert for thin liquidity
        if depth.total_liquidity < 100000:  # Less than $100k liquidity
            print(f"⚠️  THIN LIQUIDITY: {depth_event.symbol}")
            print(f"   Total Liquidity: ${depth.total_liquidity:,.2f}")
            print(f"   Market Impact (1000 shares): {depth.market_impact_1000:.4f}")
    
    # Register callbacks
    analytics.add_spread_callback(spread_callback)
    analytics.add_imbalance_callback(imbalance_callback)
    analytics.add_depth_callback(depth_callback)
    
    # Subscribe to symbols
    symbols = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"]
    for symbol in symbols:
        await analytics.subscribe_symbol(symbol)
    
    print(f"Monitoring order book analytics for {len(symbols)} symbols...")
    
    # Keep running
    try:
        while True:
            await asyncio.sleep(1)
            
            # Print periodic summary
            summary = await analytics.get_market_summary()
            print(f"\\nMarket Summary ({datetime.now().strftime('%H:%M:%S')}):")
            print(f"  Average Spread: {summary.avg_spread_bps:.2f} bps")
            print(f"  Market Imbalance: {summary.market_imbalance:.3f}")
            print(f"  Total Liquidity: ${summary.total_liquidity:,.0f}")
            
    except KeyboardInterrupt:
        await analytics.stop()
```

### Advanced Spread Analysis

```python
async def advanced_spread_analysis():
    analytics = OrderBookAnalytics(OrderBookConfig(
        enable_spread_decomposition=True,
        enable_cross_venue_analysis=True,
        historical_analysis_days=30
    ))
    
    await analytics.start()
    
    symbol = "AAPL"
    
    # Multi-venue spread analysis
    venues = ["NASDAQ", "NYSE", "BATS", "IEX"]
    venue_spreads = {}
    
    for venue in venues:
        order_book = await get_order_book_snapshot(symbol, venue)
        spread_analysis = await analytics.analyze_spread(
            order_book=order_book,
            venue=venue,
            include_decomposition=True
        )
        venue_spreads[venue] = spread_analysis
    
    print(f"{symbol} Multi-Venue Spread Analysis:")
    for venue, spread in venue_spreads.items():
        print(f"\\n{venue}:")
        print(f"  Spread: {spread.spread_bps:.2f} bps")
        print(f"  Adverse Selection: {spread.adverse_selection_component:.4f}")
        print(f"  Inventory Cost: {spread.inventory_component:.4f}")
        print(f"  Processing Cost: {spread.processing_component:.4f}")
    
    # Find best venue for execution
    best_venue = min(venue_spreads.keys(), key=lambda v: venue_spreads[v].spread)
    print(f"\\nBest Venue for Execution: {best_venue}")
    
    # Arbitrage opportunities
    arbitrage_opps = await analytics.detect_arbitrage_opportunities(
        symbol=symbol,
        venue_spreads=venue_spreads,
        min_profit_bps=1.0  # Minimum 1 bp profit
    )
    
    if arbitrage_opps:
        print(f"\\nArbitrage Opportunities:")
        for opp in arbitrage_opps:
            print(f"  Buy {opp.buy_venue} @ ${opp.buy_price:.4f}")
            print(f"  Sell {opp.sell_venue} @ ${opp.sell_price:.4f}")
            print(f"  Profit: {opp.profit_bps:.2f} bps")
    
    # Historical spread patterns
    historical_patterns = await analytics.analyze_historical_spreads(
        symbol=symbol,
        days=30,
        granularity="1h"
    )
    
    print(f"\\nHistorical Spread Patterns:")
    print(f"  Average Spread: {historical_patterns.avg_spread_bps:.2f} bps")
    print(f"  Spread Volatility: {historical_patterns.spread_volatility:.2f}")
    print(f"  Time-of-Day Pattern:")
    
    for hour, avg_spread in historical_patterns.hourly_averages.items():
        print(f"    {hour:02d}:00 - {avg_spread:.2f} bps")
    
    # Spread prediction
    spread_forecast = await analytics.predict_spread(
        symbol=symbol,
        forecast_horizon_minutes=30,
        include_confidence_intervals=True
    )
    
    print(f"\\nSpread Forecast (30 minutes):")
    print(f"  Predicted Spread: {spread_forecast.predicted_spread_bps:.2f} bps")
    print(f"  Confidence Interval: [{spread_forecast.lower_bound:.2f}, {spread_forecast.upper_bound:.2f}] bps")
    print(f"  Forecast Confidence: {spread_forecast.confidence:.3f}")
    
    await analytics.stop()
```

### Market Depth and Liquidity Analysis

```python
async def market_depth_analysis():
    analytics = OrderBookAnalytics(OrderBookConfig(
        enable_depth_calculation=True,
        enable_liquidity_analysis=True,
        depth_levels=[100, 500, 1000, 2500, 5000, 10000]
    ))
    
    await analytics.start()
    
    symbols = ["AAPL", "MSFT", "GOOGL", "TSLA"]
    
    for symbol in symbols:
        order_book = await get_order_book_snapshot(symbol)
        
        # Comprehensive depth analysis
        depth_analysis = await analytics.calculate_comprehensive_depth(
            order_book=order_book,
            max_depth_levels=20,
            include_order_count=True
        )
        
        print(f"\\n{symbol} Market Depth Analysis:")
        print(f"  Total Bid Liquidity: ${depth_analysis.total_bid_liquidity:,.2f}")
        print(f"  Total Ask Liquidity: ${depth_analysis.total_ask_liquidity:,.2f}")
        print(f"  Depth Ratio (Bid/Ask): {depth_analysis.depth_ratio:.3f}")
        
        # Market impact analysis
        impact_analysis = await analytics.calculate_market_impact(
            order_book=order_book,
            order_sizes=[100, 500, 1000, 2500, 5000],
            side="both"
        )
        
        print(f"  Market Impact Analysis:")
        for size, impact in impact_analysis.buy_impacts.items():
            sell_impact = impact_analysis.sell_impacts[size]
            print(f"    {size} shares: Buy {impact:.4f}, Sell {sell_impact:.4f}")
        
        # Liquidity concentration
        concentration = await analytics.analyze_liquidity_concentration(
            order_book=order_book,
            price_range_bps=50  # Within 50 bps of mid
        )
        
        print(f"  Liquidity Concentration (50 bps):")
        print(f"    Bid Concentration: {concentration.bid_concentration:.3f}")
        print(f"    Ask Concentration: {concentration.ask_concentration:.3f}")
        print(f"    Concentration Ratio: {concentration.concentration_ratio:.3f}")
        
        # Order size distribution
        size_distribution = await analytics.analyze_order_size_distribution(
            order_book=order_book
        )
        
        print(f"  Order Size Distribution:")
        print(f"    Small Orders (<100): {size_distribution.small_orders_pct:.1%}")
        print(f"    Medium Orders (100-1000): {size_distribution.medium_orders_pct:.1%}")
        print(f"    Large Orders (>1000): {size_distribution.large_orders_pct:.1%}")
        print(f"    Average Order Size: {size_distribution.avg_order_size:.0f}")
    
    # Cross-symbol liquidity comparison
    liquidity_ranking = await analytics.rank_symbols_by_liquidity(
        symbols=symbols,
        ranking_criteria=["total_liquidity", "depth_consistency", "spread_tightness"]
    )
    
    print(f"\\nLiquidity Ranking:")
    for i, (symbol, score) in enumerate(liquidity_ranking, 1):
        print(f"  {i}. {symbol}: {score:.3f}")
    
    await analytics.stop()
```

### Order Book Imbalance Prediction

```python
async def imbalance_prediction_analysis():
    analytics = OrderBookAnalytics(OrderBookConfig(
        enable_imbalance_prediction=True,
        prediction_horizon_seconds=30,
        enable_ml_models=True
    ))
    
    await analytics.start()
    
    symbol = "AAPL"
    
    # Real-time imbalance monitoring with prediction
    async def monitor_imbalances():
        while True:
            order_book = await get_order_book_snapshot(symbol)
            
            # Current imbalance analysis
            current_imbalance = await analytics.detect_imbalance(order_book)
            
            # Predict future price movement based on imbalance
            prediction = await analytics.predict_price_movement(
                order_book=order_book,
                imbalance=current_imbalance,
                horizon_seconds=30
            )
            
            print(f"\\n{symbol} Imbalance Analysis ({datetime.now().strftime('%H:%M:%S')}):")
            print(f"  Current Imbalance: {current_imbalance.imbalance_ratio:.3f}")
            print(f"  Weighted Imbalance: {current_imbalance.weighted_imbalance:.3f}")
            print(f"  Depth Imbalance: {current_imbalance.depth_imbalance:.3f}")
            
            print(f"  Price Prediction (30s):")
            print(f"    Direction: {prediction.predicted_direction}")
            print(f"    Magnitude: {prediction.predicted_change:.4f}")
            print(f"    Confidence: {prediction.confidence:.3f}")
            print(f"    Probability Up: {prediction.probability_up:.3f}")
            
            # Generate trading signals based on imbalance
            if abs(current_imbalance.imbalance_ratio) > 0.6 and prediction.confidence > 0.7:
                signal_type = "BUY" if current_imbalance.imbalance_ratio > 0 else "SELL"
                print(f"  🎯 TRADING SIGNAL: {signal_type}")
                print(f"     Strength: {abs(current_imbalance.imbalance_ratio):.3f}")
                print(f"     Expected Return: {prediction.expected_return:.4f}")
            
            await asyncio.sleep(5)  # Update every 5 seconds
    
    # Historical imbalance analysis
    historical_imbalances = await analytics.analyze_historical_imbalances(
        symbol=symbol,
        days=7,
        granularity="1min"
    )
    
    print(f"Historical Imbalance Analysis (7 days):")
    print(f"  Average Imbalance: {historical_imbalances.avg_imbalance:.3f}")
    print(f"  Imbalance Volatility: {historical_imbalances.imbalance_volatility:.3f}")
    print(f"  Prediction Accuracy: {historical_imbalances.prediction_accuracy:.3f}")
    print(f"  Profitable Signals: {historical_imbalances.profitable_signals_pct:.1%}")
    
    # Start real-time monitoring
    await monitor_imbalances()
    
    await analytics.stop()
```

## Integration Examples

### Trading Strategy Integration

```python
async def order_book_trading_strategy():
    from nautilus_trader_engine.trading import TradingStrategy
    
    class OrderBookStrategy(TradingStrategy):
        def __init__(self, analytics):
            super().__init__()
            self.analytics = analytics
            self.imbalance_threshold = 0.7
            self.spread_threshold_bps = 15
        
        async def on_order_book_update(self, order_book):
            symbol = order_book.symbol
            
            # Analyze current order book
            imbalance = await self.analytics.detect_imbalance(order_book)
            spread_analysis = await self.analytics.analyze_spread(order_book)
            
            # Check for trading opportunities
            if (abs(imbalance.imbalance_ratio) > self.imbalance_threshold and 
                spread_analysis.spread_bps < self.spread_threshold_bps):
                
                if imbalance.imbalance_ratio > self.imbalance_threshold:
                    # Strong buy imbalance - place buy order
                    await self.place_buy_order(
                        symbol=symbol,
                        size=100,
                        price=order_book.best_bid + 0.01,  # Aggressive pricing
                        reason=f"Buy imbalance: {imbalance.imbalance_ratio:.3f}"
                    )
                
                elif imbalance.imbalance_ratio < -self.imbalance_threshold:
                    # Strong sell imbalance - place sell order
                    await self.place_sell_order(
                        symbol=symbol,
                        size=100,
                        price=order_book.best_ask - 0.01,  # Aggressive pricing
                        reason=f"Sell imbalance: {imbalance.imbalance_ratio:.3f}"
                    )
        
        async def on_spread_change(self, spread_event):
            # Adjust strategy based on spread changes
            if spread_event.spread_analysis.spread_bps > 25:
                # Wide spread - reduce activity
                await self.reduce_position_size(factor=0.5)
            elif spread_event.spread_analysis.spread_bps < 5:
                # Tight spread - increase activity
                await self.increase_position_size(factor=1.5)
    
    # Initialize integrated strategy
    analytics = OrderBookAnalytics(OrderBookConfig())
    await analytics.start()
    
    strategy = OrderBookStrategy(analytics)
    
    # Connect order book updates to strategy
    analytics.add_order_book_callback(strategy.on_order_book_update)
    analytics.add_spread_callback(strategy.on_spread_change)
    
    await strategy.start()
    print("Order book-based trading strategy activated")
```

### Risk Management Integration

```python
async def order_book_risk_integration():
    from nautilus_trader_engine.risk import RiskManager
    
    analytics = OrderBookAnalytics(OrderBookConfig())
    risk_manager = RiskManager()
    
    await analytics.start()
    await risk_manager.start()
    
    # Monitor order book for risk signals
    async def risk_callback(order_book_event):
        if order_book_event.type == "LIQUIDITY_CRISIS":
            crisis = order_book_event.crisis
            
            # Reduce position limits during liquidity crisis
            await risk_manager.emergency_liquidity_adjustment(
                symbol=crisis.symbol,
                liquidity_reduction=crisis.severity,
                reason=f"Liquidity crisis: {crisis.description}"
            )
        
        elif order_book_event.type == "EXTREME_IMBALANCE":
            imbalance = order_book_event.imbalance
            
            # Increase monitoring for extreme imbalances
            if abs(imbalance.imbalance_ratio) > 0.9:
                await risk_manager.increase_monitoring_level(
                    symbol=imbalance.symbol,
                    level="critical",
                    reason=f"Extreme imbalance: {imbalance.imbalance_ratio:.3f}"
                )
        
        elif order_book_event.type == "SPREAD_WIDENING":
            spread = order_book_event.spread
            
            # Adjust execution algorithms for wide spreads
            if spread.spread_bps > 50:
                await risk_manager.adjust_execution_parameters(
                    symbol=spread.symbol,
                    max_participation_rate=0.1,  # Reduce market impact
                    reason=f"Wide spread: {spread.spread_bps:.2f} bps"
                )
    
    analytics.add_risk_callback(risk_callback)
    
    print("Order book-based risk management active")
```

## Performance Optimization

### High-Frequency Processing

```python
# Configure for high-frequency order book processing
hf_config = OrderBookConfig(
    update_frequency_ms=1,  # 1ms updates
    enable_parallel_processing=True,
    max_worker_threads=16,
    enable_memory_optimization=True,
    cache_size=50000,
    enable_incremental_updates=True
)

analytics = OrderBookAnalytics(hf_config)
```

### Memory Management

```python
# Optimize memory usage for large-scale processing
memory_config = MemoryConfig(
    max_order_book_history=1000,
    enable_compression=True,
    garbage_collection_interval=60,
    max_memory_usage_mb=4096
)

analytics = OrderBookAnalytics(OrderBookConfig(
    memory_config=memory_config
))
```

## Best Practices

### Data Quality and Validation

1. **Order Book Validation**
   - Verify price-time priority
   - Check for crossed markets
   - Validate sequence numbers

2. **Latency Management**
   - Monitor feed latency
   - Implement latency compensation
   - Use high-resolution timestamps

3. **Error Handling**
   - Handle missing data gracefully
   - Implement circuit breakers
   - Log anomalies for analysis

### Scalability Considerations

1. **Multi-Symbol Processing**
   - Use parallel processing
   - Implement efficient data structures
   - Optimize memory allocation

2. **Real-Time Requirements**
   - Minimize processing latency
   - Use lock-free data structures
   - Implement proper threading

## Conclusion

The Order Book Analytics Engine provides a comprehensive, high-performance solution for real-time order book analysis in institutional trading environments. With sophisticated spread analysis, market depth calculation, imbalance detection, and clustering analysis capabilities, it enables advanced market microstructure analysis and trading strategy development.

The engine's combination of real-time processing, historical analysis, and predictive capabilities makes it suitable for production use in demanding financial environments while maintaining the sub-millisecond performance requirements of high-frequency trading systems.