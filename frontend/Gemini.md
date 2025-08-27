# Gemini Code Assist Directives: Frontend (/frontend)

This document provides specific instructions for working within the /frontend directory. This service is the unified "cockpit" for the entire Nautilus Trader ATS, providing the user with a seamless, powerful, and intuitive interface for all trading, analysis, and development activities. These rules are in addition to the global directives in the root GEMINI.md file.

## 1\. Service Overview & Core Mission

The mission of the /frontend service is to create a modern, responsive, multi-platform application that democratizes algorithmic trading. It must cater to two distinct user personas: the non-technical retail investor ("Sarah") and the professional quantitative analyst ("Michael"). The UI must be powerful yet accessible, providing a seamless experience across web, mobile, and desktop platforms.

## 2\. Key Technologies & Libraries (Mandatory)

You must use the following "Best-of-Breed" stack for all frontend development:

- **Framework:** Next.js (React 18, TypeScript) with the App Router.
- **UI Components:** Material-UI (MUI) for a consistent design system.
- **State Management:** Redux Toolkit for all global application state.
- **Charting & Visualization:**
  - **TradingView Advanced Charts:** For primary, professional-grade market charting.
  - **react-financial-charts:** For supplementary, custom financial plots.
  - **Plotly Dash:** For interactive, data-rich analytical dashboards.
- **No-Code Strategy Builder:** Google's **Blockly**.
- **AI Chat Interface:** **Lobe Chat**.
- **Multi-Platform Support:**
  - **React Native:** For the mobile application.
  - **Electron:** For the desktop application.
  - **Progressive Web App (PWA):** Service workers must be implemented for offline capabilities.

## 3\. Core Responsibilities & Key Features

This service is responsible for implementing the following key user-facing features:

- **Real-Time Trading Dashboard:** A comprehensive dashboard displaying live portfolio value, P&L, positions, and market data.
- **Advanced Order Management:** An intuitive interface for placing, modifying, and canceling all supported order types (Market, Limit, Stop, VWAP, TWAP, Iceberg).
- **No-Code to Clean Code Pipeline:** The Blockly interface must generate clean, human-readable Python code that serves as a learning tool for users to graduate to the Python Studio.
- **"Glass Box" UI / Decision Event Explorer:** A critical transparency feature that must visualize the entire Kafka event chain for every trade, linking it to AI insights and sentiment data to build user trust.
- **AI Interfaces:**
  - An embedded **Lobe Chat** shell for all natural language interactions with the AI Assistant.
  - Visualizations for AI-driven insights, including SHAP explanations, sentiment topic clouds, and predictive forecasts.
- **Multi-Platform Experience:** Ensure a consistent user experience across web, mobile (with push notifications and biometrics), and desktop (with multi-monitor support and local backtesting capabilities).
- **Future-Ready Interfaces:** Implement the foundational components for **Voice Trading** (via Whisper integration) and **AR Trading Interfaces** (via WebXR).

## 4\. Integration Patterns & Data Flow (Strict)

- **API Interaction Protocol:** The frontend is a client of the backend microservices. It must not contain any business logic.
  - **Primary Data Fetching:** All standard data fetching (e.g., portfolio state, historical data) must be done via the **GraphQL** endpoint exposed by the API Gateway.
  - **Real-Time Data Streaming:** All live, real-time data updates (e.g., market prices, order fills, AI alerts, "Glass Box" events) **MUST** be handled via a single, persistent **WebSocket** connection. Polling for real-time data is strictly forbidden.
- **Authentication:** All user authentication and authorization must be handled via **OAuth2/OIDC** protocols, integrating with the backend security services. The frontend is responsible for managing JWT tokens securely.

## 5\. Local Coding Standards & Patterns

- **Component Structure:** All UI elements must be created as functional React components using hooks. Follow the Atomic Design methodology (Atoms, Molecules, Organisms) for structuring components to ensure reusability.
- **Styling:** Use CSS-in-JS with MUI's styling solution (styled). Avoid global CSS files except for defining the base theme and typography.
- **State Management:** All global application state (e.g., user authentication, portfolio data, broker connection status) must be managed through the Redux store. Local component state can be managed with useState or useReducer.
- **Performance:** The application must be highly performant. Target a Lighthouse score of 90+ for performance, and ensure all real-time updates render in under 200ms.

## 6\. Testing Protocol

- **Unit & Component Testing:** All components and utility functions must have **\>95% unit test coverage** using **Jest** and **React Testing Library**.
- **End-to-End (E2E) Testing:** All critical user flows (e.g., login, placing a live trade, building a strategy with Blockly, viewing the "Glass Box" for a trade) must be covered by **Cypress E2E tests**.

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
