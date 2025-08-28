# Gemini Code Assist Directives: Agentic AI Assistant (/ai_assistant)

This document provides specific instructions for working within the /ai_assistant directory. This service is the central intelligence hub—the "brain"—of the Nautilus Trader ATS. Your work here powers every intelligent feature, from natural language interaction and predictive analytics to autonomous agent-driven trading and development. Adherence to these directives is paramount. These rules are in addition to the global directives in the root GEMINI.md file.

## 1\. Service Overview & Core Mission

The mission of the /ai_assistant service is to provide a sophisticated, multi-agent AI framework that delivers advanced analytics, proactive intelligence, and seamless user interaction. It is responsible for two primary domains:

1. **Trading Intelligence:** Empowering users by analyzing market data, generating predictive insights, managing risk, and orchestrating trading strategies.
2. **Development Intelligence:** Assisting in the development, debugging, and optimization of the ATS itself through a collaborative, two-agent architecture.

## 2\. Key Technologies & Libraries (Mandatory)

You must use the following "Best-of-Breed" stack for all development within this directory:

- **AI Orchestration:**
  - **LangGraph:** The master orchestrator for all complex, stateful, multi-agent workflows.
  - **Archon:** The central "command center" and Model Context Protocol (MCP) server for the developer agents (OpenHands, Goose).
- **Agent Frameworks:**
  - **TradingAgents:** The foundational framework for the specialized financial agents (Analyst, Researcher, Risk Manager, Trader).
  - **OpenHands:** The "Specialist" agent for all fine-grained, code-level tasks (writing/debugging strategies, refactoring).
  - **Codename Goose:** The "General Contractor" agent for all high-level, system-wide workflows and DevOps tasks.
- **Data & Analytics:**
  - **OpenBB:** The primary tool for financial data integration.
  - **FinRL:** The framework for all reinforcement learning-based strategy optimization.
  - **PyOD:** The library for all anomaly detection in trading data and user behavior (UEBA).
  - **Optuna:** The framework for all hyperparameter tuning.
  - **SHAP:** The library for ensuring all model predictions are explainable.
- **NLP & Deep Learning:**
  - **Hugging Face Transformers:** The framework for all advanced financial text analysis (sentiment, summarization).
  - **PyTorch:** The primary deep learning framework for training custom models (e.g., LSTMs).
- **RAG (Retrieval-Augmented Generation) Pipeline:**
  - **RAGFlow:** The core engine for the RAG pipeline.
  - **Unstructured.io:** The tool for parsing complex, unstructured documents (e.g., PDFs, SEC filings).

## 3\. Core Responsibilities & Logic

This service is responsible for the following key functions:

- **Multi-Agent Coordination:** You will implement and manage the collaborative workflows between all specialized agents. The **Analyst** generates insights, the **Researcher** fetches data, the **Risk Manager** assesses exposure, and the **Trader** can be authorized to act on their collective decision.
- **Natural Language Understanding & Interaction:** This service is the sole endpoint for all natural language commands coming from the **Lobe Chat** interface. It must accurately interpret user intent and route tasks to the appropriate agent or workflow.
- **Proactive Intelligence (RAG):** You will implement the "Researcher" agent, which must continuously and autonomously monitor external data sources, process new information through the RAG pipeline, and update the vector databases in real-time.
- **Predictive Analytics & Anomaly Detection:** This service hosts and serves all predictive models (e.g., LSTMs for price forecasting) and anomaly detection models (PyOD). It must provide a real-time inference engine with caching for high performance.
- **Reinforcement Learning & Optimization:** You will build and maintain the **RLOps pipeline** for FinRL. This includes automated training, model versioning in MinIO, drift detection, and triggering retraining based on performance degradation.
- **AI-Assisted Development:** This service orchestrates the OpenHands and Codename Goose agents via Archon, enabling them to assist with writing, debugging, refactoring, and deploying code for the entire ATS.

## 4\. Integration Patterns & Data Flow (Strict)

- **Communication Protocol:** This service **MUST** be completely decoupled. All communication with other services (e.g., Trading Engine, UI) must occur asynchronously via the **Apache Kafka event bus**. Direct API calls are forbidden.
- **Consumed Events:**
  - Listens to user query topics (e.g., user.command.ai_query).
  - Listens to market data topics for analysis (e.g., market.data.bar.equity.spot.nyse.aapl).
  - Listens to system health topics for performance prediction.
- **Produced Events:**
  - Publishes actionable insights (e.g., ai.insight.prediction, ai.insight.sentiment).
  - Publishes risk alerts (e.g., ai.alert.anomaly_detected).
  - Publishes trade signals that the Trading Engine can act upon.
  - Publishes development tasks for the developer agents.
- **Database Interaction:**
  - **Qdrant/pgvector/Elasticsearch/Redis:** Stores and retrieves all vector embeddings for the RAG pipeline.
  - **ClickHouse:** Queries large-scale historical data for model training and analysis.
  - **MinIO/S3:** Stores and versions all trained ML model artifacts.

## 5\. Performance & Coding Standards

- **Inference Latency:** The real-time model inference engine must have a target latency of **sub-millisecond (<1ms)** for all critical predictive models.
- **Code Quality:** All Python code must be fully type-hinted and adhere to flake8 standards.
- **Concurrency:** Use asyncio for all I/O-bound operations to ensure the service remains non-blocking and highly responsive.

## 6\. Testing Protocol

- **Unit Testing:** All AI models, agent logic, and utility functions must have **\>95% unit test coverage** using **Pytest**.
- **Integration Testing:** All Kafka and API interactions must be validated with integration tests against containerized dependencies.
- **Model Validation:** A rigorous validation process must be implemented for all predictive models, including backtesting against unseen historical data and benchmarking for accuracy (e.g., >90% for sentiment, <5% RMSE for price forecasts).
- **E2E Workflow Testing:** Critical multi-agent workflows (e.g., a full RAG query, an AI-driven trade signal) must be covered by end-to-end tests.

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
