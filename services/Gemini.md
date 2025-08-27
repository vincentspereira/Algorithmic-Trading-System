# Gemini Code Assist Directives: Backend Microservices (/services)

This document provides specific instructions for working within the /services directory. This directory contains all the backend microservices that support the core trading and AI functionalities of the Nautilus Trader ATS. Each service must be a self-contained, independently deployable application with a single, clear responsibility. These rules are in addition to the global directives in the root GEMINI.md file.

## 1\. Service Overview & Core Mission

The mission of the services within this directory is to provide the specialized, decoupled functionalities that form the backbone of the trading platform. These services handle everything from market data ingestion and order management to portfolio tracking and risk analysis. They are the "organs" of the system, each performing a vital function and communicating through the central nervous system—the Apache Kafka event bus.

## 2\. Universal Principles for All Services

Every microservice developed within this directory MUST adhere to the following universal principles:

- **Single Responsibility:** Each service must be designed to do one thing and do it well.
- **Decoupling:** Services **MUST NOT** communicate directly with each other via API calls. All inter-service communication **MUST** be asynchronous via the Apache Kafka event bus.
- **Statelessness:** Services should be stateless wherever possible, storing any required state in a dedicated database (like Redis or PostgreSQL) to allow for easy scaling and resilience.
- **Technology Diversity:** While Python is the primary language, you may use other languages (like Go) if it is demonstrably better for a specific, high-throughput task (e.g., Market Data Service).
- **Health Checks:** Every service must expose a /health endpoint that Kubernetes can use for liveness and readiness probes.

## 3\. Individual Service Directives

### Market Data Service

- **Core Responsibilities:** This service is the sole gateway for all external market data. It is responsible for collecting, processing, normalizing, and distributing both real-time and historical market data for all supported asset classes.
- **Key Technologies:** Python or Go for high-throughput data processing.
- **Integration Patterns:**
  - **Data Ingestion:** Connects to multiple external data providers (Yahoo Finance, Finnhub, Alpaca, etc.) via their respective APIs.
  - **Fallback Mechanism:** Must implement the multi-source data feed with an automated fallback mechanism. If the primary source fails, it must automatically switch to the next provider in the chain for that asset class.
  - **Produced Events:** Publishes normalized data to specific Kafka topics using the hierarchical naming convention (e.g., market.data.tick.equity.spot.nyse.aapl, market.data.bar.1m.forex.spot.oanda.eur-usd).
  - **Database Interaction:** Stores historical bar and tick data in **ClickHouse** for backtesting and analytics. Stores raw data files (e.g., Parquet) in **MinIO/S3**.

### Order Management System (OMS)

- **Core Responsibilities:** This service manages the entire lifecycle of a trade order. It is responsible for order validation, pre-trade compliance checks, execution management, and processing fills. In later phases, it will incorporate a **Smart Order Router** and advanced algorithmic order types (VWAP, TWAP).
- **Key Technologies:** Python with a focus on low-latency optimizations. Integrates **QuickFIX/J** or **FIX8** for institutional connectivity via the FIX protocol.
- **Integration Patterns:**
  - **Consumed Events:** Listens for order.request events from the Trading Engine.
  - **Produced Events:** Publishes order status updates throughout the lifecycle (e.g., order.accepted, order.filled, order.rejected, order.canceled) to Kafka.
  - **External Interaction:** Communicates directly with broker APIs (Interactive Brokers, Alpaca, etc.) and FIX gateways to send orders and receive execution reports.

### Risk Manager

- **Core Responsibilities:** This service is the central hub for monitoring and controlling trading risk in real-time. It performs pre-trade checks, calculates portfolio-level risk metrics (e.g., VaR), and monitors for exposure limit breaches.
- **Key Technologies:** Python with real-time processing libraries. Integrates **PyOD** for anomaly detection and **SHAP** for explaining AI-driven risk decisions.
- **Integration Patterns:**
  - **Consumed Events:** Listens to oms.pre_trade_check events to validate orders before execution. Listens to portfolio.state.update events to recalculate overall portfolio risk. Listens to market data events to re-evaluate risk based on price changes.
  - **Produced Events:** Publishes risk check responses (e.g., oms.check_passed, oms.check_failed). Publishes real-time risk metrics (e.g., risk.metrics.portfolio_var). Publishes critical risk alerts (e.g., risk.alert.limit_breach).

### Portfolio Manager

- **Core Responsibilities:** This service is the single source of truth for all portfolio and position data. It is responsible for tracking asset allocations, calculating performance attribution, and managing rebalancing workflows.
- **Key Technologies:** Python with **NumPy** and **Pandas**. Integrates **PyPortfolioOpt** and **Riskfolio-Lib** for advanced portfolio optimization.
- **Integration Patterns:**
  - **Consumed Events:** Listens to order.filled events from the OMS to update positions.
  - **Produced Events:** Publishes portfolio.state.update events to Kafka whenever a portfolio's state changes.
  - **Database Interaction:** Persists the authoritative state of all portfolios in **PostgreSQL**. Pushes snapshots of portfolio state to **Redis** for low-latency cache access by the frontend and other services. Provides data to **DuckDB** for offline analytics.

### Market Scanner

- **Core Responsibilities:** This service provides real-time market scanning across a large universe of symbols based on user-defined criteria, using the custom volume-weighted indicators.
- **Key Technologies:** Python or Go for high-throughput data processing.
- **Integration Patterns:**
  - **Consumed Events:** Listens to all relevant real-time market data streams from Kafka.
  - **Produced Events:** Publishes scan results (e.g., a ranked list of symbols matching a "bullish VWAP crossover" scan) to a dedicated Kafka topic (e.g., scanner.result.bullish_vwap_crossover).

### Customer Service Bot

- **Core Responsibilities:** This service powers the automated customer support functionality. It uses the RAG pipeline to answer user questions about the platform.
- **Key Technologies:** Python, LangChain.
- **Integration Patterns:**
  - **Consumed Events:** Listens for user.command.support_query events originating from the chat interface.
  - **Produced Events:** Publishes support.response events back to Kafka to be relayed to the user.
  - **Database Interaction:** Queries the **Qdrant/pgvector** databases to retrieve relevant information from the knowledge base to answer questions.

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
