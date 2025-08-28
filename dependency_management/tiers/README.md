# Dependency Tiers

This directory contains the tier configuration files for the dependency management system.

## Tier Structure

### Tier 1: Critical Dependencies (`tier1_critical.json`)
**Monitoring**: Daily  
**Alert Threshold**: Immediate  
**SLA**: <2 hours response time

Core components essential to trading operations:
- Trading Engine (NautilusTrader, nautilus_ibapi)
- Event Bus (Apache Kafka, Schema Registry)
- AI Framework (LangChain, LangGraph)
- API Layer (FastAPI, gRPC)

### Tier 2: Important Dependencies (`tier2_important.json`)
**Monitoring**: Daily  
**Alert Threshold**: Standard  
**SLA**: <24 hours response time

Components supporting core functionality:
- Technical Analysis (TA-Lib, bukosabino/ta)
- Portfolio Management (PyPortfolioOpt, Riskfolio-Lib)
- Machine Learning (PyTorch, Transformers, FinRL)
- Quantitative Finance (QuantLib, VectorBT)

### Tier 3: Supporting Dependencies (`tier3_supporting.json`)
**Monitoring**: Weekly  
**Alert Threshold**: Batch  
**SLA**: <72 hours response time

Components enhancing user experience:
- Frontend (React, Next.js)
- Visualization (react-financial-charts, Plotly Dash)
- No-Code (Blockly)
- AI Interfaces (Lobe Chat)

### Tier 4: Infrastructure Dependencies (`tier4_infrastructure.json`)
**Monitoring**: Weekly  
**Alert Threshold**: Summary  
**SLA**: <1 week response time

Components supporting operations:
- Monitoring (Prometheus, Grafana, Jaeger)
- Databases (PostgreSQL, ClickHouse, Redis)
- Infrastructure (Docker, Kubernetes, Istio)
- Security (Bandit, security scanners)

## File Format

Each tier file follows this JSON structure:

```json
{
  "tier": "tier1",
  "name": "Critical Dependencies",
  "description": "Core components essential to trading operations",
  "dependencies": [
    {
      "name": "nautilus_trader",
      "type": "trading_engine",
      "criticality": "critical",
      "repository": "https://github.com/nautechsystems/nautilus_trader",
      "fork": "https://github.com/vincentspereira/nautilus_trader",
      "customizations": ["Rust performance enhancements"],
      "monitoring_schedule": "daily",
      "alert_threshold": "immediate"
    }
  ]
}
```

## Modification Guidelines

When modifying tier files:
1. Validate JSON syntax
2. Ensure all required fields are present
3. Test with `python test_dependency_system.py`
4. Update customization tracking if applicable
5. Run integration tests

## Dependency Types

- `trading_engine` - Core trading functionality
- `event_bus` - Message bus and streaming
- `ai_framework` - AI and machine learning
- `technical_analysis` - Technical indicators
- `portfolio_optimization` - Portfolio management
- `risk_management` - Risk assessment
- `frontend_framework` - UI frameworks
- `visualization` - Charts and dashboards
- `database` - Data storage
- `monitoring` - System monitoring
- `security_scanning` - Security tools

## Alert Thresholds

- `immediate` - Real-time alerts for critical issues
- `standard` - Normal notification flow
- `batch` - Grouped with other notifications
- `summary` - Weekly summary only