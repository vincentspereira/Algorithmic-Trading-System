# Gemini Code Assist Directives: Core Trading Engine (/nautilus_trader_engine)

This document provides specific instructions for working within the /nautilus_trader_engine directory. This is the heart of the Nautilus Trader ATS. Adherence to these directives is critical for system performance, stability, and correctness. These rules are in addition to the global directives in the root GEMINI.md file.

## 1\. Service Overview & Core Mission

This directory contains the implementation of the core trading engine, which is responsible for all backtesting, live trading, order management, and strategy execution. The primary mission is to build a high-performance, event-driven engine that achieves **research-to-production parity**, meaning a strategy that is backtested here must function identically in a live environment with no code changes.

## 2\. Key Technologies & Libraries (Mandatory)

You must use the following stack for all development within this directory:

- **Core Framework:** **NautilusTrader**. All strategy, execution, and data handling logic must be built upon this institutional-grade framework.
- **Performance-Critical Paths:** Any new, ultra-low latency logic (e.g., custom order matching, market data parsing) must be written in **Rust** and exposed to the Python services.
- **Technical Analysis:**
  - Primary: **TA-Lib** (ta-lib-python)
  - Secondary: ta (bukosabino/ta)
- **Data Handling:** **NumPy** and **Pandas** for all numerical and data-frame operations.
- **High-Speed Research:** **VectorBT** is the designated tool for GPU-accelerated, vectorized backtesting for research purposes.
- **Options Analytics:** All options pricing and risk calculations must be handled by a dedicated microservice that uses the **QuantLib** library. Do not implement options logic directly within this engine; instead, create clients to call the QuantLib service.

## 3\. Core Responsibilities & Logic

This service is responsible for the following key functions:

- **Strategy Execution:** Host and execute all trading strategies, whether they are generated from the Blockly no-code builder, written in the Python Studio, or suggested by the AI.
- **Order & Position Management:** Manage the full lifecycle of orders (routing, execution, fills) and maintain an accurate, real-time state of all trading positions.
- **Multi-Asset Support:** All logic must be asset-class agnostic, supporting stocks, ETFs, futures, options, forex, and cryptocurrencies.
- **Paper and Live Trading Modes:** The engine must support seamless switching between a paper trading account (with Interactive Brokers) and live trading accounts.
- **Custom Technical Indicators:** You will be responsible for implementing and integrating a comprehensive suite of **custom volume-weighted indicators**. This includes, but is not limited to:
  - VW SMA (55/34/13/5 Day)
  - VW EMA (13/5 Day)
  - VW MACD & Histogram
  - VW MFI (14 Day) & VW SMA of MFI
  - Market Normalization with 21/8 Day VW ATR
  - Strength / Weakness (based on Avg. HLC & ATR)
  - Choppy Market Index (21/8 Day)
  - Buy/Sell Easier Day

## 4\. Integration Patterns & Data Flow (Strict)

- **Communication Protocol:** This service **MUST** be completely decoupled from all other services. All communication, both inbound and outbound, must occur asynchronously via the **Apache Kafka event bus**. Direct API calls to or from this service are strictly forbidden.
- **Consumed Events:**
  - Listens to market data topics (e.g., market.data.tick.crypto.spot.binance.btcusd).
  - Listens to AI insight topics (e.g., ai.insight.prediction) for signals.
  - Listens to user command topics (e.g., user.command.run_backtest).
- **Produced Events:**
  - Publishes order requests to the Order Management System (e.g., oms.order.request).
  - Publishes backtest results (e.g., engine.backtest.result).
  - Publishes real-time strategy state and P&L updates.
- **Database Interaction:**
  - For backtesting, the engine must fetch historical data from **ClickHouse**.
  - It should not write directly to the primary PostgreSQL database; instead, it publishes events that other services will use to update their own state.

## 5\. Performance & Coding Standards

- **Latency Target:** The core event processing loop must be optimized for microsecond-level latency.
- **Code Quality:** All Python code must be fully type-hinted and adhere to flake8 standards.
- **Concurrency:** Use asyncio for all I/O-bound operations to ensure the engine remains non-blocking.

## 6\. Testing Protocol

- **Unit Testing:** All new logic, especially for custom indicators and risk calculations, must have **\>95% unit test coverage** using **Pytest**.
- **Integration Testing:** All Kafka consumer/producer logic must be validated with integration tests against a containerized Kafka instance.
- **Backtesting Validation:** A suite of regression tests must be maintained to ensure that a standard set of strategies produce identical backtest results after any code changes, guaranteeing determinism.

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

**Usage Instructions:**

- The above-mentioned documents must be referenced for each phase’s implementation, ensuring alignment with requirements, designs, and tasks.
- Use /docs/complete_requirements.md, /docs/complete_designs.md, and /docs/complete_tasks.md as primary references for phase-specific details.
- Cross-reference /docs/comprehensive_system_architecture.md for architectural guidance and /docs/01. Features, Phases & Integration Strategy - Algorithmic Trading System.md for overarching feature and integration strategies.
- For specific documentation needs (e.g., APIs, testing, deployment), refer to the respective specialized documents.
- Maintain traceability by linking code, configurations, and tests to document IDs and requirements (e.g., // @REFERENCE: req ID, doc path).
