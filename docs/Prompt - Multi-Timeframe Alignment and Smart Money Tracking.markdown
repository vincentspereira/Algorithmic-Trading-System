**Prompt: Implement Multi-Timeframe Alignment and Smart Money Tracking for Algorithmic Trading System**

**Objective:**

Enhance the NautilusTrader-based Algorithmic Trading System by adding **Multi-Timeframe Alignment** (confirming signals across multiple timeframes for accuracy) and **Smart Money Tracking** (detecting institutional flows via volume/order book analysis) as foundational infrastructure features in Phase 1. These features must initially use **open source/free resources** (e.g., Yahoo Finance, Alpha Vantage free tier, Binance for crypto) during paper trading, with a modular design to support future integration with **paid services** (e.g., Bloomberg, Refinitiv, Polygon.io) for live trading. These are foundational infrastructure features to be added in Phase 1, affecting data handling, indicators, trading engine, AI Assistant, and related components. Use the existing architecture (Kafka event bus, NautilusTrader engine, custom indicators) as the base. The implementation must account for unbuilt components (e.g., AI Agentic Assistant, RAGFlow) by including placeholders/interfaces for their future integration in Phase 3. Align with the **5-Pillar Strategy Architecture** (Signal Generation, Risk Management, Regime Adaptation, Execution, Performance Tracking) and prioritize retail trader accessibility.

**Core Requirements:**

- **Multi-Timeframe Alignment:**
  - **Purpose:** Improve signal reliability by confirming lower-timeframe signals (e.g., 5m) with higher timeframes (e.g., 1h, 1d), reducing false positives.
  - **Initial Resources:** Use free sources like Yahoo Finance (OHLCV data), Alpha Vantage (free tier for stocks), and Binance (crypto tick data) for paper trading.
  - **Future Integration:** Design with a **DataProvider** interface to swap in paid services (e.g., Interactive Brokers, Polygon.io, etc. for real-time tick data) without code changes.
  - **Integration:**
    - Enhance Market Data Service to handle multi-timeframe subscriptions via Kafka.
    - Extend each and every Technical Indicator, Candlestick Pattern, and Trading Strategy for multi-timeframe logic.
  - **Retail Focus:** Provide simple explanations (e.g., "Daily trend confirms 5m buy signal") in logs/UI for novices.
- **Smart Money Tracking:**
  - **Purpose:** Detect institutional "smart money" flows using volume imbalances, order book analysis, and microstructure metrics (e.g., cumulative delta).
  - **Initial Resources:** Use Binance order book data (free via WebSocket API) and Yahoo Finance volume data. Implement basic volume analysis with TA-Lib.
  - **Future Integration:** Abstract analysis logic to support paid order book feeds (e.g., Refinitiv's Level 2 data) for live trading.
  - **Integration:**
    - Add detection to Market Data Service, publishing signals to Kafka (e.g., market.smart_money.alert).
    - Enhance each and every Technical Indicator, Candlestick Pattern, and Trading Strategy for smart money metrics.
  - **Retail Focus:** Log actionable insights (e.g., "Large buy volume detected") for retail users.

**Architectural Integration:**

- **Market Data Service:**
  - Enhance to subscribe to multi-timeframe data (e.g., market.data.1m.AAPL, market.data.1h.AAPL) using free sources.
  - Develop an aggregator microservice (using Pandas/NumPy) to build higher-timeframe bars from low-timeframe data (e.g., 1m to 1h).
  - Implement a DataProvider interface for source abstraction (e.g., YahooFinanceProvider, PolygonIOProvider).
  - Publish aggregated data to Kafka with schema validation via Schema Registry.
- **Trading Engine (NautilusTrader):**
  - Update Strategy class to consume multi-timeframe data (e.g., via on_bar for multiple timeframes).
  - Add smart money signals to entry/exit logic (e.g., buy if 5m VW MACD bullish and smart money buying detected).
  - Support backtesting with simulated multi-timeframe data.
- **Custom Indicators:**
  - Extend TA-Lib/Bukosabino-ta as well as the already developed Technical Indicators and Candlestick Patterns for multi-timeframe versions (e.g., VW MACD_1h confirming VW MACD_5m).
  - Add smart money indicators (e.g., volume imbalance ratio, cumulative delta) using NumPy.
- **Affected Features:**
  - **Risk Manager (PyOD/SHAP):**
    - Use smart money for anomaly detection (e.g., flag unusual volume spikes)
    - Add multi-tieframe VaR
  - **Market Scanner:** Add multi-timeframe filters (e.g., bullish on 1h and 1d) and smart money ranks (e.g., high institutional volume).
  - **Portfolio Manager (PyPortfolioOpt/Riskfolio-Lib):** Use multi-timeframe correlations for optimization.
  - **Backtesting Engine (VectorBT/TradingGym):** Simulate multi-timeframe aggregation and smart money flows.
  - **OMS:** Use smart money for execution timing (e.g., execute during high institutional liquidity).
  - **Market Microstructure Analysis:** Enhance with smart money flow detection (e.g., large hidden orders).
  - **Future AI Assistant/RAGFlow (Unbuilt):**
    - Create placeholder interfaces (e.g., GuidanceInterface) for recommending multi-timeframe checks (e.g., "Confirm 5m signal on 1h") and smart money scans.
    - Log events to Kafka (e.g., ai.recommendation.multi_timeframe) for future RAG queries.
  - **Intelligent User Guidance System (Unbuilt):**
    - Update Tool Taxonomy placeholder with multi-timeframe/smart money tools
    - Suggest next steps (e.g., "After 5m scan, confirm on 1h")

**Implementation Steps (Phase 1 Focus):**

1. **Market Data Enhancements:**
    - Implement DataProvider interface with free sources (Yahoo Finance, Alpha Vantage, Binance). Test data retrieval (<100ms latency).
    - Develop aggregator microservice: Resample 1m bars to 5m/1h/1d using Pandas/NumPy.
    - Publish to Kafka topics (e.g., market.data.1h.\*). Test aggregation accuracy (MAE <0.01%).
    - Enhance fallback mechanism to handle multi-timeframe switches (<50ms).
2. **Smart Money Tracking:**
    - Implement volume imbalance and cumulative delta analysis using Yahoo Finance volume and Binance order book data (WebSocket).
    - Use NumPy for calculations.
    - Publish alerts to Kafka (market.smart_money.alert). Test detection accuracy (>85%, <5% false positives) with simulated institutional flows.
3. **Trading Engine Updates:**
    - Modify Strategy class to handle multi-timeframe Bar objects (e.g., on_bar_5m, on_bar_1h).
    - Add smart money signals to generate_signal (e.g., require volume imbalance > threshold). Test in paper trading.
4. **Custom Indicators:**
    - Extend each and every Technical Indicator & Candlestick Pattern for multi-timeframe (e.g., VW MACD_1h). Test computation <1ms/tick.
    - Add smart money indicators (e.g., VW MFI with institutional weighting). Test accuracy >90%.
5. **Affected Components:**
    - Risk Manager: Add smart money anomaly detection (PyOD); multi-timeframe VaR. Test SHAP explanations (>80% scores).
    - Market Scanner: Add multi-timeframe filters/smart money ranks. Test scan latency <1s for 10k symbols.
    - Portfolio Manager: Use multi-timeframe correlations in Riskfolio-Lib. Test optimization <5s.
    - Backtesting: Simulate multi-timeframe/smart money in VectorBT. Test GPU acceleration.
    - OMS: Enhance router with smart money timing. Test impact <0.5%.
    - Microstructure: Add smart money flow detection. Test liquidity MAE <1%.
    - **Future AI/RAG Hooks/Intelligent User Guidance System:**
        - AI: Define GuidanceInterface for multi-timeframe/smart money recommendations. Log events to Kafka for future AI Assistant.
        - RAG: Add placeholder RAG queries in Qdrant/pgvector for documentation grounding.
        - Intelligent User Guidance System: Update taxonomy placeholder; test suggestion relevance >90%.

**Testing & Validation:**

- **Unit Tests:** >90% coverage for aggregator, indicators, and smart money logic (Pytest).
- **Integration Tests:** Verify multi-timeframe data flows via Kafka (Postman). Test free data source reliability.
- **End-to-End Tests:** Simulate paper trading workflow (e.g., multi-timeframe signal + smart money alert → backtest).
- **Performance:** Ensure data aggregation <100µs; test with Locust (10k symbols).
- **Future-Proofing:** Validate DataProvider abstraction with mock paid service (e.g., Polygon.io).
- **Security:** Log all actions to Apache Iceberg for audits; test compliance with FINRA standards.

**Deliverables:**

- Updated Market Data Service with multi-timeframe support and DataProvider interface.
- Aggregator microservice for higher-timeframe bars.
- Smart money detection logic and indicators.
- Enhanced Trading Engine and affected components.
- Placeholder interfaces for AI Assistant/RAGFlow.
- Documentation: Developer guide, user guide for retail traders.
- Test suite: 100+ cases covering all scenarios.