# Dependency Management Guide

## Overview

The Algorithmic Trading System uses a **containerized approach** to dependency management, ensuring isolated, reproducible, and consistent environments across all services. Each service manages its own dependencies within Docker containers, eliminating the need for global package installations and preventing version conflicts.

## Core Principles

### 1. **Isolated Dependencies**
- Each service has its own dependency stack
- No shared global packages between services
- Complete isolation prevents version conflicts
- Services can use different versions of the same library

### 2. **Containerized Environment**
- All dependencies run within Docker containers
- Consistent environment across development, testing, and production
- No local installation of programming language packages required
- Easy cleanup and environment reset

### 3. **No Global Installations**
- Python packages are NOT installed globally on the host system
- Node.js packages are NOT installed globally on the host system
- All runtime dependencies are containerized
- Only Docker and Docker Compose are required on the host

## Dependency Tiers

Dependencies are organized into four tiers based on their criticality to the system:

### Tier 1: Critical
Essential components without which the system cannot function:
- NautilusTrader
- Apache Kafka
- LangChain
- TA-Lib/ta-lib-python
- VectorBT
- FinRL
- PyOD

### Tier 2: Important
Important components that enhance core functionality:
- PyPortfolioOpt
- Riskfolio-Lib
- Stock-Prediction-Models
- LSTM-Neural-Network-for-Time-Series-Prediction
- TradingGym
- QuantLib
- Transformers
- PyTorch
- SHAP

### Tier 3: Supporting
Supporting components that provide additional capabilities:
- Blockly
- react-financial-charts
- Plotly Dash
- Unstructured.io
- Qdrant
- PostgreSQL/pgvector
- DuckDB
- ClickHouse

### Tier 4: Infrastructure
Infrastructure components required for deployment and operations:
- Kubernetes
- Docker
- Istio
- NGINX
- Prometheus
- Grafana
- Jaeger
- Loki
- Unleash
- Apache Iceberg
- Bandit

## Service-Specific Dependency Management

### Python Services

#### Nautilus Trader Engine
- **Location**: [`nautilus_trader_engine/requirements.txt`](../nautilus_trader_engine/requirements.txt)
- **Type**: Production service (Phase 1)
- **Dependencies**: NautilusTrader, data feeds, database connectors
- **Container**: Python 3.11 slim base image

#### AI Assistant Service
- **Location**: [`ai_assistant/requirements.txt`](../ai_assistant/requirements.txt)
- **Type**: Placeholder service (Future phases)
- **Dependencies**: OpenAI, Anthropic, LangChain, FastAPI, ML libraries
- **Container**: Python 3.11 slim base image

**Python Dependency Structure:**
```
service_name/
├── requirements.txt          # Production dependencies
├── Dockerfile               # Container configuration
├── README.md               # Service documentation
└── [source code files]
```

### Node.js Services

#### Frontend Service
- **Location**: [`frontend/package.json`](../frontend/package.json)
- **Type**: Placeholder service (Future phases)
- **Dependencies**: Next.js, React, TypeScript, Tailwind CSS
- **Container**: Node.js 18 Alpine base image

**Node.js Dependency Structure:**
```
frontend/
├── package.json            # Dependencies and scripts
├── package-lock.json       # Locked dependency versions
├── Dockerfile             # Multi-stage container build
├── README.md              # Service documentation
└── [source code files]
```

## Dependency Management System

The system includes comprehensive tooling for managing dependencies:

### Automated Monitoring
- Daily checks for Tier 1 & 2 dependencies
- Weekly checks for Tier 3 & 4 dependencies
- Security vulnerability scanning
- Version drift detection

### Notification System
- Multi-channel notifications (Teams, Discord, Email)
- Priority-based alerting
- Escalation protocols

### Testing Environment
- Docker-based isolated testing environments
- Automated integration testing
- Rollback capabilities

### Health Dashboard
- Real-time dependency status
- Version tracking
- Security metrics
- Performance indicators

### Security Scanning
- Static analysis with Bandit for Python code
- Dependency vulnerability scanning
- Threat modeling integration

### Customization Tracking
- Changelog maintenance for customizations
- Conflict detection during updates
- Semantic versioning for modified components

## Placeholder Protocol

All incomplete implementations must be tagged with:
```
// @PLACEHOLDER: [reason], [requirement ID]
```

This ensures proper tracking and follow-up of incomplete work.

## Incremental Development Protocol

The system follows a three-step development process:
1. **Analyze** - Review existing codebase
2. **Compare** - Assess against requirements
3. **Execute** - Modify or build as needed

This ensures alignment with system requirements and architectural principles.