**System Overview**

This project aims to build a comprehensive, enterprise-grade **algorithmic trading system** from the ground up. The platform's core philosophy is a "Best-of-Breed" integration strategy, selecting the best open-source projects for each major component to create a powerful, modular foundation. The system caters to both non-technical users (via simplicity and no-code options) and professional traders/analysts (via enterprise-grade features), leveraging AI Agents and Agentic AI extensively.

The architecture is designed as a set of distinct microservices that communicate through an **Apache Kafka event bus**. This event-driven approach decouples services, provides data replayability for robust testing, and scales to handle high-frequency data streams for professional traders. The system's standout feature is a sophisticated **Agentic AI Assistant**, which acts as the platform's "brain," enabling users to manage trading, research, and analysis via natural language commands. The core trading engine is **NautilusTrader**, a high-performance, Python-based platform with Rust components, designed for event-driven backtesting and live trading across all asset classes. The Agentic AI Assistant leverages **TradingAgent** for multi-agent decision-making, **OpenBB** for financial data integration, and **TA-Lib/ta-lib-python** (primary wrapper) & **Bukosabino/ta** (secondary wrapper) for technical analysis, forming a robust AI-driven trading brain.

The system incorporates advanced forecasting from **Stock-Prediction-Models** and **LSTM-Neural-Network-for-Time-Series-Prediction**, with real-time predictions enabled by **Real-time-stock-market-prediction** for live trading. **VectorBT** provides GPU-accelerated backtesting, while **TradingGym** complement NautilusTrader for flexible strategy development and simulated environments. Additional features include portfolio optimisation (**PyPortfolioOpt**, **Riskfolio-Lib**), anomaly detection (**PyOD**), no-code strategy building (**Blockly**), visualisation (**react-financial-charts**, **Plotly Dash**), explainable AI (**SHAP**), reinforcement learning (**FinRL**), and advanced NLP (**Transformers**, **PyTorch**), alongside options analytics (**QuantLib**).j

**Key Characteristics**

- High Performance: Microsecond-level latency for trading operations
- Scalable: Horizontal scaling across multiple nodes
- Resilient: Fault-tolerant with automatic failover
- Secure: Enterprise-grade security with zero-trust architecture
- Observable: Comprehensive monitoring and alerting

**Universal Architecture Principles (Mandatory)**

1. **Microservices Architecture**
    - Service Decomposition: Each business capability is a separate service
    - Independent Deployment: Services can be deployed independently
    - Technology Diversity: Services can use different technologies
    - Fault Isolation: Failure in one service doesn't affect others
    - Automated Self-Healing: Microservices are designed with automated self-healing mechanisms to detect and restore normal functionality for faulty components, minimising downtime and preventing cascading failures.
2. **Event-Driven Architecture**
    - Asynchronous Communication: Services communicate via events
    - Event Sourcing: All state changes are captured as events
    - CQRS: Command Query Responsibility Segregation
    - Event Streaming: Real-time event processing
3. **Cloud-Native Design**
    - Container-First: All services are containerised
    - Kubernetes Native: Designed for Kubernetes orchestration
    - 12-Factor App: Follows 12-factor application principles
    - Infrastructure as Code: All infrastructure is code-defined
4. **API-First Design**
    - RESTful APIs: Standard REST interfaces
    - GraphQL: Flexible query interface
    - WebSocket: Real-time communication
    - gRPC: High-performance inter-service communication

**Core Services and Capabilities**

1. **Trading Engine**
    - System supports multiple asset classes (stocks, ETFs, futures, options, forex, and crypto).
    - Purpose: Execute trading strategies and manage orders
    - Technology: Python/Rust for performance-critical paths
    - Key Features:
        - Order routing and execution
        - Strategy execution
        - Position management
        - Trade settlement
        - Paper and Live Trading Modes: Provides seamless integration with broker accounts (starting with Interactive Brokers) for both paper and live trading, with the ability to switch between modes within the user interface.
        - **Custom Technical Analysis:**
            - A world-class technical analysis engine that combines traditional indicators with sophisticated volume-weighting methodology, and comprehensive candlestick pattern recognition.
            - **Volume-Weighted Indicators:** The system includes a comprehensive suite of custom-developed, volume-weighted technical indicators (e.g., VW SMA, VW EMA, VW MACD, VW MFI) and market analysis metrics (e.g., Normalised ATR, Choppy Market Index, Buy/Sell Easier Day) built with TA-Lib and NumPy. These are fully integrated into the NautilusTrader engine for use in strategy development and analysis.
            - **Enhanced Technical Indicators:**
                - Complete Technical Analysis Suite:
                  - **Trend Indicators:**
                    - **Traditional:** SMA, EMA, Hull MA, Kaufman AMA, DEMA, TEMA, WMA, etc.
                    - **Volume-Weighted**: VWMA, VW EMA, VW Keltner EMA, etc.
                    - Enhanced with alpha = 1.0 / n methodology
                  - **Momentum Indicators:**
                    - **Traditional:** RSI, MACD, Stochastic, Williams %R, CCI, ROC, PPO, TRIX, etc.
                    - **Volume-Weighted**: VW RSI, VW MACD, etc.
                    - Enhanced with volume confirmation and proper gain/loss calculations
                  - **Volatility Indicators:**
                    - **Traditional:** Bollinger Bands, ATR, Keltner Channels, Donchian Channels, etc.
                    - **Volume-Weighted**: VW ATR, VW ATRP (Normalized ATR), etc.
                    - Enhanced with volume weighting and smoothing
                  - **Volume Indicators:**
                    - VWAP, OBV, A/D Line, MFI, Chaikin Oscillator, Volume ROC, Ease of Movement, NVI, etc.
            - **Candlestick Pattern Analysis:**
                - **Reversal Patterns:**
                  - Hammer/Hanging Man (bullish/bearish based on trend context)
                  - Shooting Star/Inverted Hammer
                  - Engulfing (Bullish/Bearish)
                  - Morning Star (3-candle bullish reversal)
                  - Evening Star (3-candle bearish reversal), etc.
                - **Indecision/Continuation Patterns:**
                  - Spinning Top (indecision)
                  - Marubozu (strong directional)
                  - Tweezer Top (bearish reversal)
                  - Tweezer Bottom (bullish reversal), etc.
            - **Proper Volume Weighting**: Using methodology of (price × volume).ewm() / volume.ewm()
            - **Alpha Calculations**: Consistent alpha = 1.0 / period for all EMA calculations
            - **Multiple Price Variants**: OHLC typical price, High-Low midpoint calculations
            - **Enhanced Signal Generation**: Signal boundaries, strength calculations, confidence levels
            - **Volume Confirmation**: Pattern analysis enhanced with volume confirmation
            - **Comprehensive Error Handling**: Graceful degradation when modules unavailable
            - **Integration Features:**
                - **Concurrent Execution**: All indicators calculated in parallel
                - **Signal Aggregation**: Volume-weighted consensus signals with confidence scoring
                - **Pattern Recognition**: Real-time candlestick pattern detection with trend context
                - **Volume Confirmation**: Enhanced pattern reliability through volume analysis
                - **Backward Compatibility**: Seamless integration with existing codebase
                - Real-time signal generation and aggregation
                - Enhanced confidence scoring and pattern strength analysis
2. **Configure Paper and Live Trading**
    - **Action**: Set up **NautilusTrader** for integration with Interactive Brokers.
    - **Details**:
        - Connect to both paper trading and live trading accounts via Interactive Brokers.
        - Implement seamless switching between paper and live modes within the interface.
        - Ensure compliance with broker-specific requirements and regulations.
    - **Purpose**: Enables users to test strategies in a risk-free paper trading environment before transitioning to live trading.
    - Paper Trading: A key objective of Phase 4 is to connect the entire integrated system to a paper trading account. The integration plan for this phase explicitly includes configuring NautilusTrader engine's pre-built Interactive Brokers integration to connect to a paper trading account.
    - **Live Trading**: Phase 4 also introduces live trading capabilities. The plan includes enabling live trading in the NautilusTrader engine, expanding the API to manage live trading operations, and enabling live trading data feeds. The end goal of this phase is for a user to execute and monitor trades in a live trading account through the custom web application.
    - **Note**:
        - This system, during testing and initially after deployment, will first be tried using the Interactive Broker's Paper Trading Account. And only after this system is thoroughly tested till full satisfaction, will we be moving to Live Trading using the Interactive Broker's Live Trading Account.
        - Further, during the paper trading, we do not want to spend any money on the development of any features and so we will like to use free and open source repositories / systems as well as freely available market data sources like Yahoo Finance, etc.
        - But during the Live Trading, we will be subscribing to Interactive Broker's paid Market Data subscriptions.
        - Also, the system will have Multi-Source Data Feeds with Fallback mechanism, which implements a multi-source data feed strategy to ensure uninterrupted data availability.
        - The system uses a primary source with a cascade of fallback providers for each asset class, managed automatically.
        - Further, for this system the primary broker will be Interactive Broker (IBKR) for Paper Trading as well as for Live Trading.
        - Other brokers, like Oanda, Coinbase, etc., would be additionally integrated with this system at a later stage.
3. **Portfolio Manager**
    - Purpose: Manage portfolios and asset allocation
    - Technology: Python with NumPy/Pandas
    - Key Features:
        - Portfolio optimisation
        - Asset allocation
        - Performance attribution
        - Rebalancing
4. **Risk Manager**
    - Purpose: Monitor and control trading risks
    - Technology: Python with real-time processing
    - Key Features:
        - Real-time risk monitoring
        - VaR calculations
        - Exposure limits
        - Stress testing
    - Real-time Risk Dashboard: Visualises live risk metrics in the Next.js frontend.
5. **Market Data Service**
    - Purpose: Collect, process, and distribute market data
    - Technology: Python/Go for high throughput
    - Key Features:
        - Real-time data feeds
        - Historical data storage
        - Data normalisation
        - Market data distribution
        - Multi-Source Data Feeds with Fallback: Implements a multi-source data feed strategy to ensure uninterrupted data availability. The system uses a primary source with a cascade of fallback providers for each asset class, managed automatically.
        - Asset-Class Specific Fallback Chains: The fallback mechanism is configured per asset class (e.g., Stocks, Forex, Crypto) to use the most relevant data providers.
6. **Configure Data Feed and Fallback Mechanism**
    - **Action**: Implement a multi-source data feed with fallback:
        - **Primary**: Yahoo Finance.
        - **Fallbacks**: Alpha Vantage, Finnhub, Investing.com, CME Group, Twelve Data, Polygon, Barchart, SpiderRock, TradingCharts, Oanda.
    - **Details**: Use Kafka to stream data, with logic to switch sources on failure.
    - **Purpose**: Ensures uninterrupted data availability.
    - **Trading Instruments:** The system supports a wide range of asset classes to cater to diverse trading needs.
        - Stocks & ETFs (global equities and exchange-traded funds).
        - Stock Futures & Index Futures (e.g., E-mini S&P 500, Nasdaq-100).
        - Stock Options & Index Options (e.g., calls, puts on equities and indices).
        - Forex, Forex Futures, & Forex Options (e.g., EUR/USD, G10 currencies).
        - Commodities, Commodity Futures, & Commodity Options (e.g., crude oil, gold, corn).
        - Cryptocurrency, Cryptocurrency Futures, & Cryptocurrency Options (e.g., Bitcoin, Ethereum).
    - **Data Sources for Live Trading**:
        - Subscribe to Interactive Brokers' real-time market data and historical data once paper trading is validated.
    - **Historical Data**:
        - Use free sources for paper trading and
        - Interactive Brokers for live trading.
    - **Free Data Sources for Paper Trading**:
        - **Stocks & ETFs**
            - Yahoo Finance: Free historical and delayed data for global equities and ETFs.
            - Interactive Brokers
            - Alpha Vantage: Free APIs for real-time and historical data, including fundamentals and technical indicators.
            - Finnhub: Free-tier APIs for real-time stock prices and company fundamentals.
            - Twelve Data
            - Polygon.io
        - **Stock Futures & Index Futures**
            - Yahoo Finance: Free historical and delayed data for global equities and ETFs.
            - Interactive Brokers
            - Investing.com: Free real-time/delayed quotes for global index futures (e.g., S&P 500, Nikkei 225).
            - CME Group: Free delayed data for equity index futures (e.g., E-mini S&P 500).
            - Barchart: Delayed futures prices for indices like Dow Jones and S&P 500.
        - **Stock Options & Index Options**
            - Yahoo Finance: Free historical and delayed data for global equities and ETFs.
            - Interactive Brokers
            - Cboe Daily Market Statistics: Free delayed summary data for options trading volumes.
            - SpiderRock: Free delayed options data via APIs (e.g., OPRA feeds).
        - **Forex, Forex Futures, & Forex Options**
            - Yahoo Finance: Free historical and delayed data for global equities and ETFs.
            - Interactive Brokers
            - Oanda
            - CME Group FX Data: Delayed data for G10 and emerging market forex futures.
            - dxFeed: Multi-contributor forex data (real-time/delayed).
        - **Commodity, Commodity Futures, & Commodity Options**
            - Yahoo Finance: Free historical and delayed data for global equities and ETFs.
            - Interactive Brokers
            - TradingCharts: Free delayed quotes for commodity futures (e.g., crude oil, gold).
            - CME Group: Delayed data for commodities like oil and agricultural futures.
        - **Cryptocurrency, Cryptocurrency Futures, & Cryptocurrency Options**
            - Interactive Brokers
            - Alpha Vantage: Free crypto data APIs for Bitcoin, Ethereum, etc.
            - Coinbase
            - Binance India
    - **Data Feed Fallback Mechanism**:
        - Data retrieval follows this order: Yahoo Finance → Alpha Vantage → Finnhub → Investing.com → CME Group → Twelve Data → Polygon → Barchart → SpiderRock → TradingCharts → Oanda.
        - If one source fails, the system automatically switches to the next. This fallback mechanism should be created as per the asset class.
    - **Options Data Requirements**
        - Historical options chain data (min 5 years depth)
        - Real-time implied volatility surfaces
        - Dividend forecast integration
    - **Test the Core Engine:** Run a simple, pre-built algorithm from the NautilusTrader library to validate that the entire pipeline is working: the engine can fetch data, run a backtest, and generate results.
7. **Order Management System (OMS)**
    - Connects to various brokers, starting with Interactive Brokers, with basic order types (Market, Limit) as well as advanced and algorithmic order types (VWAP, TWAP).
    - FIX Gateway for institutional connectivity.
    - Purpose: Manage order lifecycle and execution
    - Technology: Python with low-latency optimisations
    - Key Features:
        - Order validation
        - Execution management
        - Fill processing
        - Compliance checks
8. **Market Scanner Service**
    - **Purpose**: To provide real-time market scanning across a large universe of symbols based on user-defined criteria.
    - **Technology**: Python/Go for high-throughput data processing.
    - **Key Features**:
        - Consumes real-time data streams from Kafka.
        - Applies custom filters using technical indicators (e.g., TA-Lib).
        - Streams filtered results to a dedicated, high-performance UI grid.
9. **AI-Powered Strategy Development:** Users can develop strategies through multiple interfaces:
    - **No-Code Strategy Builder:**
        - A visual drag-and-drop interface via Blockly.
        - It is designed to generate clean, human-readable Python code, creating a powerful learning pathway for users to transition from visual design to programmatic customisation.
    - **AI-Assisted Development & Debugging Agent:** Assists with Python code for strategies and integrations.
    - **Agentic AI Assistant:** Natural language commands for trading, research, and development assistance.
    - **Python Studio:** Traditional Python-based coding environment.
10. **Agentic AI Assistant:**
    - Core user-interaction model via a Chatbot.
    - Uses an Agentic **Retrieval-Augmented Generation (RAG)** pipeline to process and query user-uploaded documents.
    - Composed of a collaborative network of specialised agents (Analyst, Researcher, Risk Manager, Compliance, etc.). **All inter-agent communication will occur asynchronously via the Apache Kafka event bus.** This ensures agents are fully decoupled, enables flexible, one-to-many information flows, and creates a complete, auditable log of the AI's reasoning process.
    - Users can ask the AI to run a backtest, get portfolio status, or even place live trades.
    - **LLM-Driven Iterative Strategy Refinement:** Employs AI agents in a continuous feedback loop to analyse strategy performance, identify weaknesses, and autonomously generate optimised code, enabling full-lifecycle strategy improvement.
    - **AI Context Management with MCPs:** Utilises Model Context Protocols (MCPs) with LangChain and LangGraph to maintain conversation history and context across multiple user interactions, ensuring the AI assistant operates efficiently.
        - **Action**: Implement Model Context Protocols (MCPs) to manage AI workflows and context.
        - **Details**:
            - Use **LangChain** and **LangGraph** to:
                - Maintain conversation history and context across multiple user interactions.
                - Define workflows for task execution (e.g., query → retrieval → response).
            - Plan for optional integrations in future phases:
                - **Hugging Face Transformers** for advanced NLP tasks.
                - **PyTorch** for custom model training or fine-tuning.
            - Test context retention with multi-turn conversations (e.g., “Run a backtest” followed by “Explain the results”).
        - **Purpose**: Ensures the AI assistant operates efficiently, retains context, and scales for future enhancements.
    - **Defined AI Workflows:** Employs LangGraph to define and manage stateful workflows for complex, multi-step task execution (e.g., query → data retrieval → analysis → response).
11. **Enterprise Security and Risk Management:** Platform is built with,
    - **Zero-Trust architecture**
    - Real-time risk hub for pre-trade checks and account-level circuit breakers.
    - Role-based access control (**RBAC**)
    - Immutable audit trails for compliance in **Apache Iceberg**.
    - Feature Flags (e.g., **Unleash**) for dynamic toggling of strategies and kill-switches.
    - Static Application Security Testing (SAST) with **Bandit**, automatically scanning Python code for common security vulnerabilities.
    - User and Entity Behaviour Analytics **(UEBA)**
    - Threat Modelling by Design
    - Formalised Backup Strategy
12. **Managing Updates to Cloned Repositories**
    To balance the benefits of upstream updates with the stability of your customised system, adopt a **selective update strategy** for cloned repositories (e.g., OpenHands, Codename Goose, LangChain, LangGraph, kafka, etc.).
    - **Maintain Forked Repositories**:
        - **Treat cloned repositories as forks, customised for your system (e.g., integrating OpenHands with Kafka).**
        - **Document customisations in a changelog to track differences.**
        - **Focus on improving your fork for domain-specific needs (e.g., SDLC workflows, compliance for Lawyer Agent).**
    - **Monitor Upstream Repositories**:
      - **Use GitHub Actions to check for updates daily, notifying via Slack if changes are detected.**
      - **Example: Monitor OpenHands for security patches or new features.**
    - **Selective Update / Integration Process**:
      - **Prioritise updates for security patches, bug fixes, or relevant features.**
      - **Test updates in a staging environment using a CI/CD pipeline (e.g., GitHub Actions, Jenkins).**
      - **Require human review for major updates to assess alignment with your system.**
    - **Dependency Management**:
      - **Use Dependabot to monitor and update dependencies within cloned repositories.**
      - **Pin dependencies in lock files (e.g., requirements.txt) to prevent conflicts.**
      - **Run automated tests post-update to ensure compatibility.**
    - **Comprehensive Testing and Validation**:
      - **Implement a CI/CD pipeline with pytest, Jest, and Cypress to test updates.**
      - **Use LangSmith to evaluate agent performance after updates.**
    - **Rollback Capability:**
      - **Capability to roll back the upgrade / integration in case of any failed updates.**
    - **Contribute Back (Optional)**:
      - **Submit generalisable customisations to upstream repositories to reduce future merge conflicts.**
    - **Benefits**:
      - **Preserves your customisations while allowing critical updates.**
      - **Automates monitoring and testing, reducing manual effort.**
      - **Ensures dependency compatibility and system stability.**
    - **Notification Frequency:**
      - **Daily: Silent logging only (no notifications).**
      - **Weekly: Single consolidated message with ALL updates.**
      - **Monthly: Integration status and deployment summary.**
      - **Emergency: Immediate notification and Integration for critical security issues only.**
    - **Notification System:** The primary mode of notification should be email, including Microsoft Teams.
13. **Incorporate Custom Volume-Weighted Indicators**
    - **Action**: Extend the technical indicator framework with volume-weighted calculations using **TA-Lib** and **NumPy**.
    - **Details**:
        - Develop custom volume-weighted technical indicators (e.g., VW SMA, VW EMA, VW MACD) using TA-Lib/ta-lib-python (primary wrapper) & Bukosabino/ta (secondary wrapper) and NumPy, as specified below:
            - Beta vis-à-vis Market Index,
            - Auto Correlation,
            - Historical Annual Volatility,
            - Intraday Annual Volatility,
            - 55 Day VW SMA of Open (Entry),
            - 13 Day VW SMA of Open (Entry),
            - 5 Day VW SMA of High (Exit),
            - 5 Day VW SMA of Low (Exit),
            - 34 Day VW SMA of Open (Entry),
            - 13 Day VW SMA of High (Exit),
            - 13 Day VW SMA of Low (Exit),
            - 13 Day VW EMA of Open,
            - 5 Day VW EMA of HLC (High, Low, Close) Average (Trend Finder),
            - VW MACD of HLC Average (12 Day, 26 Day, 9 Day),
            - VW MACD Histogram of HLC Average,
            - 14 Day VW MFI of HLC Average,
            - 34 Day VW SMA of MFI (14) of HLC Average (Entry),
            - 21 Day VW SMA of MFI (14) of HLC Average (Exit),
            - Market Normalisation with 21 Day VW ATR for Positional Trades \[N\],
            - Rupee Volatility / Risk \[N x Lot Size\], (Change this to Dollar Volatility for US SEs and to Pound Sterling for LSE)
            - Contract Risk (Units) \[2N\],
            - Max. Lots that can be Traded with a Unit of x Rs. \[No. of Lots\],
            - 21 Day Average True Range Percent,
                <https://www.thebalance.com/how-average-true-range-atr-can-improve-trading-4154923>.
                - When to Use Normal ATR : On the contrary, the traditional non-normalised ATR is preferred as input in risk management or position management decisions, such as the following:
                  - Position size (typically calculated as your risk budget / current volatility as ATR)
                  - Stop loss (typically the distance of stop loss price from entry price or current price is a multiple of ATR)
                  - Profit target (same logic as stop loss, just the other direction)
                  - In general, traditional non-normalised ATR is better when you are interested in absolute dollar amounts rather than percentages, which is usually when the decision relates to your particular trading capital.
                - Average True Range (ATR) is a very useful measure of volatility, but it has downsides. Because it is derived from range (or to be precise, true range) and expressed as absolute dollar value, it is not directly comparable across securities and over time.
                - For example, a stock trading around 10 with ATR of 0.5 is actually more volatile than a stock trading around 200 with a much greater ATR of 2. The Average True Range Percent / ATRP Indicator is a variation of Welles Wilder Average True Range (ATR), which featured in his 1978 book, “New Concepts in Technical Trading Systems.”
                - It is important to remember that the indicator does not try and predict the direction of price, instead it only tries to define the current volatility in the market. Also, it tries to define current volatility in such a way that it is comparable across all markets, which is the main difference from the traditional ATR. ATR measures volatility at an absolute level, meaning lower priced stock will have lower ATR values than higher price stocks. ATRP displays the indicator as a percentage, to allow for securities trading at different prices per share to be compared.
                - How this indicator works,
                  - ATRP is used to measure volatility just as the Average True Range (ATR) indicator is.
                  - ATRP allows securities to be compared, where ATR does not.
                  - Calculation ATRP = (Average True Range / Close) * 100
                - When to Use ATRP or Normalised ATR (<https://www.macroption.com/normalised-atr/>):
                You should use ATRP (Normalised ATR) instead of the traditional, absolute dollar ATR particularly in these situations:
                - When using ATR for stock screening (to decide which stocks or securities currently have the right volatility for your strategy or trading style).
                - When using ATR as strategy filter (to decide whether the volatility is high enough or low enough to take a signal from a trading strategy, or to “turn on/off” strategies based on market volatility regime).
                - When using ATR to study seasonality or volatility patterns over long periods of time.
                - In general, Normalised ATR is better than traditional ATR in situations which involve comparing different securities or different periods of time.
            - Market Normalisation with 8 Day VW ATR for Intraday Trades [N],
            - Rupee Volatility / Risk [N x Lot Size], (Change this to Dollar Volatility for US SEs and to Pound Sterling for LSE)
            - Contract Risk (Units) [0.75N],
            - Max. Lots that can be Traded with a Unit of x Rs. [No. of Lots],
            - 8 Day Average True Range Percent,
            - Strength / Weakness (Based on 21 Day Avg. HLC & ATR) for Positional,
              Page 29 - Turtle Rules by Curtis Faith:-
              Buy Strength & Sell Weakness:
              - If all the signals come together, always Buy the Strongest Markets and Sell the Weakest Markets in a Group.
              - Subtract the Average HLC Price of 21 Days from the Last Traded Price / Close and then divide this figure by the VW ATR of 21 Days. [LTP - Avg. HLC(21)] / ATR(21)
              - The above calculation 'Normalises' the Price across the Markets.
              - The Strongest Markets have the Highest values, while the Weakest Markets have the Lowest values.
            - Strength / Weakness (Based on 8 Day Avg. HLC & ATR) for Intraday,
            - High Low Range Average for ORB,
            - 8 Day SMA Average % Change,
            - 13 Day SMA Average % Change,
            - 21 Day SMA Average % Change,
            - Buy Easier Day and Sell Easier Day,
            - 21 Day Choppy Market Index,
            - 21 Day Market Mode (Trending / Choppy),
            - 8 Day Choppy Market Index,
            - 8 Day Market Mode (Trending / Choppy)
        - Use TA-Lib/ta-lib-python (primary wrapper) & Bukosabino/ta’s (secondary wrapper) framework to extend existing indicators with volume weighting.
        - Leverage NumPy for efficient calculations of volume-weighted averages.
        - Integrate these into **NautilusTrader’s** strategy engine for use in trading logic.
        - Verify accuracy with historical data and unit tests.
    - **Purpose**: Enhances trading strategies by incorporating volume data into technical analysis for more informed decisions.

**Project Details and Guidelines**
- **System Description**:
  - Build a comprehensive, enterprise-grade algorithmic trading system using a "Best-of-Breed" integration strategy.
  - Select and integrate leading open-source projects (60+) for modularity (listed below). Support non-technical users (no-code options, natural language via Agentic AI Assistant) and professionals (high-performance features).
  - Architecture: Microservices with Apache Kafka event bus for decoupling, event-driven processing, scalability, and replayability.
  - Core engine: NautilusTrader (Python/Rust) for multi-asset trading (stocks, ETFs, futures, options, forex, crypto).
  - Key integrations: Forecasting (Stock-Prediction-Models, LSTM, Real-time-prediction), backtesting (VectorBT, TradingGym), portfolio/risk (PyPortfolioOpt, Riskfolio-Lib, PyOD), indicators (TA-Lib/ta-lib-python & Bukosabino/ta with 30+ custom volume-weighted), visualization (react-financial-charts, Plotly Dash), AI/ML (LangChain/LangGraph, TradingAgent, FinRL, SHAP, Transformers/PyTorch, QuantLib), no-code (Blockly), and more.
  - Databases: PostgreSQL/pgvector (structured/vectors), ClickHouse (time-series), Qdrant (vectors), Apache Iceberg (immutable audits), Redis (cache/GenAI vectors), DuckDB (OLAP research), InfluxDB (metrics), MinIO/S3 (objects), Elasticsearch (search/logs/RAG).
  - Features: Paper/live trading (IBKR start, expand to Alpaca/OANDA/Coinbase/FIX), multi-source data feeds with fallbacks, custom indicators (e.g., VW SMA, Normalized ATR, Choppy Market Index), Agentic AI (multi-agents, RAG, MCPs, iterative refinement), market scanner, "Glass Box" UI, voice/AR, marketplace scope, ultra-low latency (DMA, FPGAs), enterprise readiness (HA, UEBA, compliance).
- **Open-Source Repositories**

1. <https://github.com/nautechsystems/nautilus_trader>
2. <https://github.com/nautechsystems/nautilus_ibapi>
3. <https://github.com/apache/kafka>
4. <https://github.com/confluentinc/schema-registry>
5. <https://github.com/kubernetes/kubernetes>
6. <https://github.com/docker-library/docker>
7. <https://github.com/istio/istio>
8. <https://github.com/nginx/nginx>
9. <https://github.com/helm/helm>
10. <http://github.com/langchain-ai/langchain>
11. <https://github.com/langchain-ai/langgraph>
12. <https://github.com/coleam00/Archon>
13. <https://github.com/TauricResearch/TradingAgents>
14. <http://github.com/OpenBB-finance/OpenBB>
15. <https://github.com/TA-Lib/ta-lib-python>
16. <https://github.com/bukosabino/ta>
17. <https://github.com/All-Hands-AI/OpenHands>
18. <https://github.com/block/goose>
19. <https://github.com/huseinzol05/Stock-Prediction-Models>
20. <https://github.com/jaungiers/LSTM-Neural-Network-for-Time-Series-Prediction>
21. <https://github.com/victor369basu/Real-time-stock-market-prediction>
22. <https://github.com/polakowo/vectorbt>
23. <https://github.com/Yvictor/TradingGym>
24. <https://github.com/lballabio/QuantLib>
25. <https://github.com/vercel/next.js>
26. <https://github.com/fastapi/fastapi>
27. <https://github.com/grpc/grpc>
28. <https://github.com/redwoodjs/graphql>
29. <https://github.com/facebook/react>
30. <https://github.com/lobehub/lobe-chat>
31. <https://github.com/infiniflow/ragflow>
32. <https://github.com/pgvector/pgvector>
33. <https://github.com/ClickHouse/ClickHouse>
34. <http://github.com/duckdb/duckdb>
35. <https://github.com/qdrant/qdrant>
36. <https://github.com/apache/iceberg>
37. <https://github.com/redis/redis>
38. <https://github.com/influxdata/influxdb>
39. <https://github.com/minio/minio>
40. <https://github.com/quickfix-j/quickfixj>
41. <https://github.com/fix8/fix8>
42. <https://github.com/feast-dev/feast>
43. <https://github.com/tecton-ai>
44. <https://github.com/prometheus/prometheus>
45. <https://github.com/grafana/grafana>
46. <https://github.com/grafana/tempo>
47. <https://github.com/bloomberg/memray>
48. <https://github.com/elastic/elasticsearch>
49. <https://github.com/grafana/loki>
50. <https://github.com/jaegertracing/jaeger>
51. <https://github.com/prometheus/alertmanager>
52. <https://github.com/deviantony/docker-elk>
53. <https://github.com/Unleash/unleash>
54. <https://github.com/PyCQA/bandit>
55. <https://github.com/react-financial/react-financial-charts>
56. <https://github.com/plotly/dash>
57. <https://github.com/optuna/optuna>
58. <https://github.com/robertmartin8/PyPortfolioOpt>
59. <https://github.com/dcajasn/Riskfolio-Lib>
60. <https://github.com/yzhao062/pyod>
61. <https://github.com/shap/shap>
62. <https://github.com/google/blockly>
63. <https://github.com/huggingface/transformers>
64. <https://github.com/pytorch/pytorch>
65. <https://github.com/AI4Finance-Foundation/FinRL>

- **Development Approach**:
  - Incremental phases (0-6).
  - Use placeholders (// @PLACEHOLDER: reason, req ID) for incomplete parts, create GitHub Issues.
  - Follow analysis/compare/execute protocol: Analyze specs vs. code, compare diffs, execute builds/modifications.
  - Enforce code standards: Python 3.12+, Rust for latency, linting (flake8), tests (Pytest).
  - Manage deps in tiers with forks, automated monitoring (Renovate/Dependabot), CI/CD (GitHub Actions, Docker sandboxes), dashboard (React/Grafana).
- **Tools and Environment**:
  - You have access to a stateful code interpreter (Python 3.12 with libraries: numpy, pandas, sympy, etc.; no internet/pip).
  - Use it to test code snippets, validate logic (e.g., custom indicators).
  - For external info, use web/X search tools if needed (e.g., check upstream repo changes). Render citations inline for sources.
  - Output code in proper format, commit to virtual repo structure.

**Detailed Six Phase Prompt and Integration Plan**
This plan outlines the objectives and key outcomes for each of the six primary development phases, building upon the foundational work established in Phase 0 (Dependency Management). This integration plan outlines a structured, phased approach to developing a robust, enterprise-grade Algorithmic Trading System (ATS). It leverages the existing infrastructure (Docker, Kubernetes, monitoring stack) and partially implemented components (NautilusTrader, AI assistant, security) while addressing gaps and introducing advanced features. Each phase includes detailed objectives, durations, tasks, integration focus, and deliverables to ensure clarity and completeness. Each phase concludes with a mandatory **Phase-End Placeholder Review** to ensure all temporary implementations are formally addressed before proceeding, guaranteeing the integrity and completeness of the build.

**Six-Phase Integration Plan**
1. **Phase 0:** Dependency Management Setup - Establish management for 60+ components with automated monitoring and testing.
2. **Phase 1:** Core System Validation & Hardening - Stabilise security, trading engine, and APIs.
3. **Phase 2:** Frontend and Broker Integration - Develop UI and integrate Interactive Brokers.
4. **Phase 3:** AI/ML Integration - Implement AI-driven features and advanced analytics.
5. **Phase 4:** Frontend & Live Trading - Enable live trading and real-time UI integration.
6. **Phase 5:** Enterprise Readiness - Add observability, security, and compliance features.
7. **Phase 6:** System Enhancement & Future-Ready Technologies - Introduce advanced capabilities and optimise for production.

**Your Development Directives and Protocols**
You must strictly follow these two protocols for all tasks:
- Start with Phase 0 and progress sequentially through Phase 6.
- Use the existing system as the foundation, enhancing or modifying only where features are missing or misaligned.
- Ensure all developments align with the microservices, event-driven, and cloud-native architecture.
- Ensure to use Docker for all dependencies. Do not install any dependencies and libraries globally.
- **Documentation Context**
  All subsequent prompts will provide you with three sets of instructions derived directly from the official project documentation:
  - **Requirements:** Specify the "what" and "why" for each feature or component.
  - **Designs:** Detail the architectural "how" for implementation.
  - **Tasks:** Provide granular, step-by-step checklists for execution.
- **Core Directive: Incremental & Context-Aware Development**
  For every task, you MUST first **Analyse** the existing codebase, then **Compare** it against the requirements, and only then **Execute** by modifying or creating code to meet the specifications:
  - **Analyse:** Review the existing codebase to understand its current state and implementation details.
  - **Compare:** Assess the current implementation against the requirements, designs, and tasks specified in this prompt and subsequent phase-specific prompts.
  - **Execute:**
    - If the feature is fully implemented and aligned with specifications, report its completion and proceed.
    - If the feature is partially implemented or misaligned, modify the existing code to meet the new requirements.
    - If the feature is absent, develop it from scratch, adhering to the system's architectural principles.
- **Dependency Management**
  - Dependencies must be containerised; avoid global installations.
  - Each service maintains its own dependency configuration (e.g., `requirements.txt` for Python, `package.json` for Node.js) and a corresponding `Dockerfile`.
- **Placeholder Management Protocol:**
  If a feature cannot be fully implemented in a single step, you MUST tag the incomplete code with a searchable comment: // @PLACEHOLDER:. The comment must detail the reason and the missing functionality. You must also programmatically create a ticket in our project's issue tracker, tagged with "Technical-Debt" and "Placeholder." A task with a placeholder is **never** considered complete.
- **Phase-End Placeholder Review Process**
  Before any development phase can be officially signed off, a mandatory review process must be conducted to address all placeholders created during that phase. This process ensures that technical debt is managed intentionally and not by accident.
  **1. Automated Codebase Scan:** A dedicated step in the CI/CD pipeline will be configured to scan the entire codebase for the // @PLACEHOLDER: tag. If any instances of the tag are found, the pre-deployment build will fail automatically. This serves as a hard gate, preventing placeholders from accidentally slipping into the next phase or production.
  **2. Manual Backlog Review:** The development lead must conduct a formal review of all tickets in the "Placeholder Review" backlog of the issue tracking system. For each ticket, one of the following actions must be taken:
    - **Resolve:** The placeholder is prioritised, and the required work is completed. The code is updated, the tag is removed, and the ticket is closed .
    - **Defer:** In rare cases, if a placeholder is deemed non-critical for the next phase's objectives, the ticket can be formally deferred. This requires explicit approval from project leadership, and the ticket must be moved to the backlog of a specific future phase .
  A phase is only considered complete when the automated scan passes and the placeholder backlog for that phase is empty (all tickets are either resolved or formally deferred).

**Reference Documents for Nautilus Trader Development**
To ensure comprehensive guidance for each phase of the Nautilus Trader algorithmic trading system development, the Agent should refer to the following documents, located in the specified paths, for detailed requirements, designs, tasks, and other critical specifications:
- **System Requirements**:
  - **Document**: Comprehensive System Requirements
  - **Location**: /docs/complete_requirements.md
  - **Description**: Contains consolidated requirements across Phases 0-6, including user stories and acceptance criteria for all system functionalities.
- **System Designs**:
  - **Document**: Comprehensive System Designs
  - **Location**: /docs/complete_designs.md
  - **Description**: Provides detailed designs with high-level architectures, component breakdowns, and Mermaid diagrams for each phase.
- **System Tasks and Sub-Tasks**:
  - **Document**: Comprehensive System Tasks
  - **Location**: /docs/complete_tasks.md
  - **Description**: Lists over 450 detailed tasks and sub-tasks across all phases, serving as a roadmap for implementation.
- **System Architecture**:
  - **Document**: Comprehensive System Architecture
  - **Location**: /docs/comprehensive_system_architecture.md
  - **Description**: Details the system’s architecture, including overview, principles, components, data flows, technology stack, deployment, security, performance, integrations, and more.
- **Features, Phases, and Integration Strategy**:
  - **Document**: Features, Phases & Integration Strategy - Algorithmic Trading System
  - **Location**: /docs/01. Features, Phases & Integration Strategy - Algorithmic Trading System.md
  - **Description**: Outlines all features, phased development approach, and integration strategies for the Nautilus Trader platform.
- **Business Requirements**:
  - **Document**: Business Requirements Document (BRD) - Algorithmic Trading System
  - **Location**: /docs/02. Business Requirements Document (BRD) - Algorithmic Trading System.md
  - **Description**: Defines the business objectives, stakeholder needs, and high-level requirements driving the platform’s development.
- **Functional Requirements**:
  - **Document**: Functional Requirements Document (FRD) - Algorithmic Trading System
  - **Location**: /docs/03. Functional Requirements Document (FRD) - Algorithmic Trading System.md
  - **Description**: Specifies functional requirements, including user interactions, system behaviors, and operational workflows.
- **Product Requirements**:
  - **Document**: Product Requirements Document (PRD) - Algorithmic Trading System
  - **Location**: /docs/04. Product Requirements Document (PRD) - Algorithmic Trading System.md
  - **Description**: Details product-specific requirements, focusing on features, user experience, and market fit.
- **Functional Specification**:
  - **Document**: Functional Specification Document (FSD) - Algorithmic Trading System
  - **Location**: /docs/05. Functional Specification Document (FSD) - Algorithmic Trading System.md
  - **Description**: Provides detailed functional specifications, including system inputs, outputs, and processing logic.
- **Technical Specification**:
  - **Document**: Technical Specification Document (TSD) - Algorithmic Trading System
  - **Location**: /docs/06. Technical Specification Document (TSD) - Algorithmic Trading System.md
  - **Description**: Outlines technical specifications, including technology stack, APIs, and integration details.
- **System Design**:
  - **Document**: System Design Document (SDD) - Algorithmic Trading System
  - **Location**: /docs/07. System Design Document (SDD) - Algorithmic Trading System.md
  - **Description**: Describes the system’s design, including architecture patterns, component interactions, and deployment strategies.
- **Software Requirements Specification**:
  - **Document**: Software Requirements Specification (SRS) - Algorithmic Trading System
  - **Location**: /docs/08. Software Requirements Specification (SRS) - Algorithmic Trading System.md
  - **Description**: Combines functional and non-functional requirements for software development, ensuring alignment with business goals.
- **API Documentation**:
  - **Document**: API Documentation - Algorithmic Trading System
  - **Location**: /docs/09. API Documentation - Algorithmic Trading System.md
  - **Description**: Details all APIs (REST, GraphQL, WebSocket, gRPC) for system interactions, including endpoints, schemas, and usage examples.
- **Test Plan and Test Cases**:
  - **Document**: Comprehensive Test Plan and Test Cases - Algorithmic Trading System
  - **Location**: /docs/10. Comprehensive Test Plan and Test Cases - Algorithmic Trading System.md
  - **Description**: Provides a comprehensive test plan with detailed test cases for unit, integration, and end-to-end testing across all phases.
- **Configuration Management**:
  - **Document**: Configuration Management Plan - Algorithmic Trading System
  - **Location**: /docs/11. Configuration Management Plan - Algorithmic Trading System.md
  - **Description**: Defines processes for managing system configurations, version control, and dependency updates.
- **Data Flow**:
  - **Document**: Data Flow Document - Algorithmic Trading System
  - **Location**: /docs/12. Data Flow Document - Algorithmic Trading System.md
  - **Description**: Maps data flows across system components, including Kafka event streams, database interactions, and API calls.
- **Deployment Guide**:
  - **Document**: Deployment Guide - Algorithmic Trading System
  - **Location**: /docs/13. Deployment Guide - Algorithmic Trading System.md
  - **Description**: Provides step-by-step instructions for deploying the system, including Kubernetes, Helm, and Istio configurations.
- **User Documentation**:
  - **Document**: User Documentation - Algorithmic Trading System
  - **Location**: /docs/14. User Documentation - Algorithmic Trading System.md
  - **Description**: Offers user guides, tutorials, and FAQs for platform users, covering trading, strategy building, and marketplace interactions.
- The root directory and the sub-directories have **“Gemini.md”** files with the required information.

**Usage Instructions:**

- The above-mentioned documents must be referenced for each phase’s implementation, ensuring alignment with requirements, designs, and tasks.
- Use /docs/complete_requirements.md, /docs/complete_designs.md, and /docs/complete_tasks.md as primary references for phase-specific details.
- Cross-reference /docs/comprehensive_system_architecture.md for architectural guidance and /docs/01. Features, Phases & Integration Strategy - Algorithmic Trading System.md for overarching feature and integration strategies.
- For specific documentation needs (e.g., APIs, testing, deployment), refer to the respective specialized documents.

Maintain traceability by linking code, configurations, and tests to document IDs and requirements (e.g., // @REFERENCE: req ID, doc path).

# Complete Requirements Document - Algorithmic Trading System

## Overview

This document consolidates all requirements from phases 0-6 for the development of the Nautilus Trader Algorithmic Trading System. It serves as the definitive guide for the AI development agents, translating the high-level strategy into granular, testable requirements. Each phase builds upon the previous one to create a comprehensive, enterprise-grade trading platform, starting with a robust foundation and progressively adding layers of functionality, intelligence, and enterprise-grade features.

## Core Development Directives / Mandatory Development Protocols (Non-Negotiable)

### Protocol 1: Incremental & Context-Aware Development

For every task, the AI agent MUST follow this protocol:

1. **Analyse:** First, review the existing codebase to understand its current state and implementation details.
2. **Compare:** Next, assess the current implementation against the requirements, designs, and tasks specified in the prompt.
3. **Execute:** Only after completing the first two steps, proceed to develop. If a feature is absent, build it from scratch. If it is partially implemented or misaligned, modify the existing code to meet the new requirements.

### Protocol 2: Placeholder Management Protocol

To ensure project transparency, any feature that cannot be fully implemented in a single step MUST be handled via the placeholder protocol:

1. **Tagging:** You must explicitly identify any incomplete code, configuration, or feature with a standardized, searchable tag in a comment: // @PLACEHOLDER:.
2. **Detailing:** The tag must be followed by a detailed comment explaining the Reason, the exact Missing Functionality, and a reference to the Requirement ID.
3. **Ticket Creation:** An issue MUST be programmatically created in the project's issue tracker (e.g., GitHub Issues), tagged with "Technical-Debt" and "Placeholder," and assigned to a "Placeholder Review" backlog.
4. **Status Reporting:** A task involving a placeholder is NEVER considered "completed." You must report its status as "partially complete with placeholder created" and reference the new ticket number.

# Phase 0: Dependency Management Setup

## Introduction

Phase 0 establishes the foundation for managing all 60+ external dependencies and "Best-of-Breed" components. This phase implements a continuous, automated framework for monitoring, update management, and integration, ensuring system stability and security from the outset.

## Requirements

### Requirement 0.1: Best-of-Breed Component Repository Management

**User Story:** As a system architect, I want comprehensive management of all forked repositories, so that I can maintain control over critical components and ensure system stability.

#### Acceptance Criteria

1. WHEN external repositories are forked THEN they SHALL be organized into four tiers based on criticality (Critical, Important, Supporting, Infrastructure).
2. WHEN repository forks are created THEN branch protection rules and access controls SHALL be established.
3. WHEN customizations are made THEN they SHALL be tracked in a detailed changelog within each fork.
4. WHEN upstream changes occur THEN their potential impact SHALL be automatically assessed.
5. WHEN the master Git repository is created THEN it SHALL have a modular structure (/nautilus_trader_engine, /ai_assistant, /frontend).

### Requirement 0.2: Automated Update Monitoring & Notification System

**User Story:** As a DevOps engineer, I want automated, tiered monitoring of all external dependencies, so that I can proactively manage updates and security vulnerabilities.

#### Acceptance Criteria

1. WHEN monitoring workflows execute THEN they SHALL check all repositories according to their tier priority (daily for T1/T2, weekly for T3/T4).
2. WHEN security vulnerabilities are found THEN immediate, real-time emergency notifications SHALL be triggered via all channels (Teams, Discord, Email).
3. WHEN non-critical updates are detected THEN a single, consolidated weekly report SHALL be sent via all channels.
4. WHEN breaking changes are detected THEN detailed impact reports SHALL be automatically generated.
5. WHEN a monitoring workflow fails THEN a fallback mechanism SHALL ensure continuous coverage.

### Requirement 0.3: Update Integration and Testing Pipeline

**User Story:** As a software engineer, I want an automated integration pipeline for dependency updates, so that changes can be tested and integrated safely with minimal manual intervention.

#### Acceptance Criteria

1. WHEN an update is approved THEN a new integration branch SHALL be created automatically.
2. WHEN an integration branch is created THEN a comprehensive test suite SHALL be executed automatically within an isolated Docker-based environment.
3. WHEN tests pass THEN an automated pull request SHALL be created with reviewers assigned.
4. WHEN tests fail or merge conflicts are detected THEN a detailed failure report SHALL be generated and the branch flagged for manual review.
5. WHEN integration fails post-merge THEN automated rollback procedures SHALL be executed.

### Requirement 0.4: Dependency Health Dashboard

**User Story:** As a system administrator, I want a comprehensive dashboard showing the real-time health of all dependencies, so that I can monitor system-wide status proactively.

#### Acceptance Criteria

1. WHEN the dashboard is accessed THEN it SHALL display the real-time status (version, last check, security status) of all repositories, organized by tier.
2. WHEN a repository is selected THEN its update history, known vulnerabilities, and customization changelog SHALL be visible.
3. WHEN dependency relationships are visualized THEN an interactive graph SHALL show component interconnections.
4. WHEN manual overrides are needed THEN dashboard controls SHALL allow for pausing/forcing updates or triggering scans.
5. WHEN integrated with Grafana THEN the dashboard SHALL be part of the central observability stack.

# Phase 1: Core Foundation & Observability

## Introduction

Phase 1 focuses on building and stabilizing a fully observable and secure core system. It combines foundational component hardening with the essential monitoring and security controls required to support all subsequent development.

## Requirements

### Requirement 1.1: Core Trading Engine Validation (NautilusTrader)

**User Story:** As a trading system architect, I want the NautilusTrader engine thoroughly tested and validated, so that I can ensure a reliable foundation for all trading operations.

#### Acceptance Criteria

1. WHEN the engine is tested THEN comprehensive tests SHALL validate order management, risk controls, and multi-asset support (equities, forex, crypto, futures).
2. WHEN engine configuration is loaded THEN all settings SHALL be verified for correctness and compatibility.
3. WHEN engine performance is tested THEN it SHALL meet sub-millisecond order processing requirements.
4. WHEN the engine shuts down THEN all resources SHALL be properly cleaned up with no memory leaks detected by Memray.

### Requirement 1.2: Resilient Database Integration

**User Story:** As a data engineer, I want all core database systems integrated and optimized, so that I can ensure fast and reliable data operations for the entire platform.

#### Acceptance Criteria

1. WHEN database connections are established THEN they SHALL be reliable and performant for PostgreSQL/pgvector, ClickHouse, DuckDB, and Qdrant.
2. WHEN PostgreSQL is tested THEN connection pooling, transactions, and vector operations SHALL work correctly.
3. WHEN ClickHouse is tested THEN time-series data ingestion and queries SHALL perform within specified SLAs (<100ms for typical queries).
4. WHEN database failover tests are run THEN the system SHALL maintain availability with minimal data loss.

### Requirement 1.3: Multi-Protocol API Layer

**User Story:** As a developer, I want a comprehensive API layer with support for multiple protocols, so that I can build rich UIs and integrate external services effectively.

#### Acceptance Criteria

1. WHEN the API layer is deployed THEN it SHALL expose REST, GraphQL, WebSocket, and gRPC endpoints via FastAPI.
2. WHEN the REST API is used THEN it SHALL include API versioning, comprehensive error handling, and backward compatibility.
3. WHEN the GraphQL API is used THEN it SHALL support real-time subscriptions for market data and order updates.
4. WHEN the WebSocket API is used THEN it SHALL support high-frequency, bidirectional streaming of market data.
5. WHEN API tests complete THEN all endpoints SHALL have >95% test coverage and sub-200ms response times under load.

### Requirement 1.4: Foundational Observability Stack

**User Story:** As a DevOps Engineer, I want a complete observability stack configured from the start, so that I can monitor system health, debug issues effectively, and establish performance baselines.

#### Acceptance Criteria

1. WHEN Prometheus is deployed THEN it SHALL automatically scrape metrics from all core microservices.
2. WHEN Grafana is deployed THEN it SHALL have pre-configured dashboards for system health, Kafka lag, and API latency.
3. WHEN Loki is configured THEN it SHALL aggregate logs from all services, searchable within Grafana.
4. WHEN Jaeger is integrated THEN it SHALL provide end-to-end distributed tracing for API requests.
5. WHEN the observability stack is operational THEN it SHALL consume no more than 10% of baseline system resources.

### Requirement 1.5: Foundational Security Framework

**User Story:** As a security officer, I want foundational security controls implemented early, so that the entire platform is built upon a secure and compliant architecture.

#### Acceptance Criteria

1. WHEN a user authenticates THEN the system SHALL use OAuth2/OIDC protocols.
2. WHEN a user accesses an API endpoint THEN Role-Based Access Control (RBAC) SHALL be strictly enforced.
3. WHEN security tests are run THEN the Zero-Trust architecture principles (e.g., mTLS via Istio) SHALL be validated.
4. WHEN the system is scanned THEN ML-based fraud detection models SHALL be integrated and active.
5. WHEN a threat model is created THEN the STRIDE methodology SHALL be applied to all core services.

### Requirement 1.6: Scalable Event Bus Architecture (Kafka)

**User Story:** As a system architect, I want a scalable and well-organized Kafka architecture, so that the event bus can handle high data volumes and evolving system complexity.

#### Acceptance Criteria

1. WHEN Kafka topics are created THEN they SHALL adhere to a structured, hierarchical naming convention (e.g., domain.action.entity.source.symbol).
2. WHEN services consume events THEN they SHALL be able to use wildcard subscriptions to listen to relevant topic hierarchies.
3. WHEN the data feed service is active THEN it SHALL implement a multi-source fallback mechanism, publishing data to Kafka.

# Phase 2: MVP Frontend & Paper Trading

## Introduction

Phase 2 focuses on developing the Minimum Viable Product (MVP) user interface and integrating the primary broker to enable risk-free paper trading. This phase delivers the first complete end-to-end user experience.

## Requirements

### Requirement 2.1: Modern Frontend UI Development

**User Story:** As a trader, I want a modern, responsive web interface, so that I can efficiently manage my trading activities and monitor market data in real-time.

#### Acceptance Criteria

1. WHEN the frontend is built THEN it SHALL use React 18 and TypeScript.
2. WHEN the interface is accessed on different devices THEN it SHALL be fully responsive and functional.
3. WHEN real-time data is received THEN the UI SHALL update automatically via WebSocket connections without page refreshes.
4. WHEN the app is launched THEN initial shells for a Progressive Web App (PWA), React Native mobile app, and Electron desktop app SHALL be present.

### Requirement 2.2: Real-Time Trading Dashboard

**User Story:** As a trader, I want a comprehensive real-time dashboard, so that I can monitor my portfolio, positions, and market data in one centralized view.

#### Acceptance Criteria

1. WHEN the dashboard loads THEN it SHALL display the current portfolio value, P&L, and all open positions.
2. WHEN market data changes THEN the dashboard SHALL update in real-time with <100ms latency.
3. WHEN the user customizes the layout THEN their preferences SHALL be saved and restored across sessions.
4. WHEN TradingView charts are integrated THEN they SHALL display real-time market data with customizable technical indicators.

### Requirement 2.3: Broker Integration for Paper Trading (Interactive Brokers)

**User Story:** As a trader, I want full Interactive Brokers integration, so that I can execute trades and access market data through a paper trading account.

#### Acceptance Criteria

1. WHEN the system connects to IBKR THEN it SHALL establish a secure connection to the TWS/Gateway.
2. WHEN orders are placed THEN they SHALL be routed to the IBKR paper trading account.
3. WHEN market data is requested THEN IBKR data feeds SHALL provide real-time updates to the UI.
4. WHEN the UI is used THEN it SHALL provide a seamless toggle to switch between paper and (future) live trading modes.

### Requirement 2.4: No-Code Strategy Builder (Blockly)

**User Story:** As a non-technical trader, I want a visual, no-code strategy builder, so that I can create and test trading ideas without writing Python code.

#### Acceptance Criteria

1. WHEN the no-code builder is used THEN it SHALL provide a drag-and-drop interface powered by Blockly.
2. WHEN a visual strategy is saved THEN the system SHALL convert the Blockly diagram into clean, human-readable, and well-commented Python code.
3. WHEN the generated code is inspected THEN it SHALL align with the system's core strategy classes, creating a learning pathway for users.

### Requirement 2.5: AI Assistant Interface (Lobe Chat)

**User Story:** As a user, I want an intuitive chat interface to interact with the AI assistant, so that I can issue commands and ask questions using natural language.

#### Acceptance Criteria

1. WHEN the frontend is loaded THEN a chat interface powered by Lobe Chat SHALL be available.
2. WHEN a user sends a message THEN it SHALL be routed to the Agentic AI Assistant backend via the API Gateway.
3. WHEN the AI responds THEN the chat interface SHALL render the response, including markdown, code blocks, and charts.

# Phase 3: Intelligence Layer Integration

## Introduction

Phase 3 integrates the full suite of AI and Machine Learning capabilities, transforming the platform into an intelligent trading system. This phase adds the "brains" of the operation to the stable and observable core.

## Requirements

### Requirement 3.1: Agentic AI Framework

**User Story:** As an AI developer, I want a multi-agent framework, so that I can build sophisticated AI workflows for trading, research, and system development.

#### Acceptance Criteria

1. WHEN the framework is deployed THEN LangChain and LangGraph SHALL orchestrate multi-agent workflows.
2. WHEN trading tasks are run THEN specialized TradingAgents (Analyst, Risk Manager, Trader) SHALL be deployed and coordinated.
3. WHEN development tasks are run THEN the AI Knowledge Hub (Archon) SHALL serve as the central MCP server for OpenHands and Codename Goose.
4. WHEN agents communicate THEN all inter-agent communication SHALL occur asynchronously via the Apache Kafka event bus.

### Requirement 3.2: Advanced Analytics & Custom Indicators

**User Story:** As a quantitative analyst, I want access to advanced analytical tools and custom indicators, so that I can develop sophisticated and unique trading strategies.

#### Acceptance Criteria

1. WHEN the analytics engine is used THEN it SHALL support FinRL (reinforcement learning), PyOD (anomaly detection), and Optuna (hyperparameter tuning).
2. WHEN DRL strategies are developed THEN a formal RLOps Pipeline SHALL be established for continuous training, integration, and delivery.
3. WHEN custom indicators are required THEN the system SHALL provide the full suite of specified Volume-Weighted indicators (VW SMA, VW MACD, etc.) integrated into NautilusTrader.

### Requirement 3.3: Proactive Intelligence and Prediction Pipelines

**User Story:** As a trader, I want the system to provide proactive insights and predictions, so that I can stay ahead of market movements.

#### Acceptance Criteria

1. WHEN the system is running THEN a dedicated "Researcher" agent SHALL continuously monitor external data sources (news, SEC filings) via RAGFlow and update the vector database (Qdrant/pgvector).
2. WHEN predictions are needed THEN a high-performance, real-time Inference Engine SHALL serve models (e.g., LSTM, Stock Prediction Models) with sub-millisecond latency.
3. WHEN text data is analyzed THEN a Sentiment Analysis pipeline SHALL process news and social media to generate sentiment scores.

# Phase 4: Go-Live Readiness & Transparency

## Introduction

Phase 4 enables live trading with real capital and provides users with the transparency required to trust the system. This phase focuses on the critical transition from simulation to production.

## Requirements

### Requirement 4.1: Live Trading Enablement

**User Story:** As a trader, I want to deploy my validated strategies to a live trading account, so that I can execute trades with real capital.

#### Acceptance Criteria

1. WHEN live trading is enabled THEN the system SHALL provide robust WebSocket and REST APIs for live broker connectivity and order execution.
2. WHEN an order is managed THEN the frontend SHALL support the full order lifecycle (placement, modification, cancellation) for live accounts.
3. WHEN additional brokers are needed THEN the system SHALL be integrated with Alpaca in addition to Interactive Brokers.
4. WHEN a user authenticates for live trading THEN Multi-Factor Authentication (MFA) SHALL be enforced.

### Requirement 4.2: "Glass Box" UI for Transparency

**User Story:** As a user of an automated system, I want complete transparency into why a trade was made, so that I can trust the system and debug my strategies.

#### Acceptance Criteria

1. WHEN a trade is inspected THEN the "Glass Box" UI / Decision Event Explorer SHALL visualize the complete Kafka event chain that led to it.
2. WHEN the event chain is viewed THEN it SHALL show every step from the initial AI insight or signal to the final broker fill confirmation.
3. WHEN contextual data is needed THEN the UI SHALL display related information, such as sentiment trends or news events that influenced the decision.
4. WHEN an audit is performed THEN the "Glass Box" UI SHALL provide a verifiable and traceable record for every action.

### Requirement 4.3: Live Operations UI

**User Story:** As a live trader, I want a dashboard optimized for monitoring live operations, so that I can track performance and manage risk in real-time.

#### Acceptance Criteria

1. WHEN the live dashboard is viewed THEN TradingView charting SHALL be integrated with live, real-time data updates.
2. WHEN risk is monitored THEN a real-time risk interface SHALL display live metrics (e.g., VaR, exposure) and allow for manual intervention (e.g., kill switches).
3. WHEN performance is analyzed THEN a live analytics dashboard SHALL calculate and display metrics continuously.

# Phase 5: Enterprise Scaling & Advanced Security

## Introduction

Phase 5 elevates the platform to true enterprise-grade status by implementing features for high availability, advanced security, compliance, and scalability for institutional use.

## Requirements

### Requirement 5.1: High Availability & Scalability

**User Story:** As a business continuity manager, I want the platform to be highly available and scalable, so that trading operations can continue without disruption and handle institutional-level volume.

#### Acceptance Criteria

1. WHEN the platform is deployed THEN it SHALL be configured for multi-region deployment with automated disaster recovery and failover mechanisms.
2. WHEN system load increases THEN intelligent auto-scaling SHALL be triggered to manage resources efficiently.
3. WHEN a microservice fails THEN automated self-healing mechanisms SHALL detect the failure and restore functionality without manual intervention.

### Requirement 5.2: Advanced Security & Compliance

**User Story:** As a compliance officer, I want advanced security and automated compliance features, so that the platform meets all regulatory and institutional requirements.

#### Acceptance Criteria

1. WHEN an action is taken THEN it SHALL be logged to an immutable audit trail using Apache Iceberg.
2. WHEN regulatory reports are needed THEN the system SHALL automate their generation and enforcement of data retention policies.
3. WHEN user behavior is analyzed THEN a dedicated User and Entity Behavior Analytics (UEBA) solution SHALL be integrated to detect sophisticated threats.

### Requirement 5.3: Enterprise Integration & Tooling

**User Story:** As an enterprise administrator, I want the platform to integrate with standard enterprise tools and provide features for professional traders.

#### Acceptance Criteria

1. WHEN users are managed THEN the system SHALL integrate with enterprise identity providers like LDAP/Active Directory.
2. WHEN features are rolled out THEN the system SHALL use a feature flag service (Unleash) for dynamic toggling and A/B testing.
3. WHEN professional traders need tools THEN a real-time Market Scanner Service SHALL be available for opportunity discovery.
4. WHEN new quants are onboarded THEN a "Professional Trader Quick-Start" guide SHALL be available.

# Phase 6: Future Enhancements & Optimization

## Introduction

Phase 6 enhances the platform with next-generation features, including ultra-low latency infrastructure, advanced execution algorithms, extended broker support, and future-ready interfaces.

## Requirements

### Requirement 6.1: Ultra-Low Latency Infrastructure

**User Story:** As a high-frequency trading firm, I want ultra-low latency infrastructure, so that I can execute strategies at the highest possible speeds.

#### Acceptance Criteria

1. WHEN the system is deployed for HFT THEN a strategy for Direct Market Access (DMA) and server co-location SHALL be implemented.
2. WHEN maximum performance is needed THEN specialized hardware like FPGAs or SmartNICs SHALL be explored for integration.
3. WHEN code is optimized THEN advanced low-level techniques (e.g., lock-free data structures) SHALL be enforced in performance-critical paths.

### Requirement 6.2: Advanced Order Management & Broker Expansion

**User Story:** As an institutional trader, I want advanced order management and broad broker connectivity, so that I can optimize execution and access diverse liquidity pools.

#### Acceptance Criteria

1. WHEN large orders are placed THEN a smart order router with execution algorithms (TWAP, VWAP, Iceberg) SHALL be available.
2. WHEN institutional connectivity is required THEN the system SHALL support the FIX protocol (QuickFIX/J, FIX8).
3. WHEN trading other asset classes THEN broker integrations for OANDA (Forex) and Coinbase (Crypto) SHALL be available.
4. WHEN deploying to the cloud THEN the entire system SHALL be deployable via Kubernetes using Helm charts and an Istio service mesh.

### Requirement 6.3: Next-Generation AI & UI

**User Story:** As a user, I want cutting-edge AI and user interface capabilities, so that I can interact with the platform in more intuitive and powerful ways.

#### Acceptance Criteria

1. WHEN strategies are deployed THEN an AI-powered Iterative Strategy Refinement agent SHALL be available to provide optimization suggestions.
2. WHEN hands-free access is needed THEN the system SHALL support voice trading commands and AR interfaces for data visualization.
3. WHEN users need help THEN a Customer Service Bot SHALL be available to answer questions about the platform.
4. WHEN users want to share ideas THEN a Strategy Marketplace SHALL be available for publishing and subscribing to trading strategies.
5. WHEN system performance is analyzed THEN Memray and Grafana Tempo SHALL be integrated for memory profiling and deep tracing.