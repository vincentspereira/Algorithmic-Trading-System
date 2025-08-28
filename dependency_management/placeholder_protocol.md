# Placeholder Protocol

## Overview

The Placeholder Protocol ensures systematic tracking and resolution of incomplete code implementations across the Algorithmic Trading System. This protocol maintains code quality while enabling incremental development.

## Placeholder Syntax

All placeholders MUST use this exact format:

```
// @PLACEHOLDER: <description>, <requirement_id>
```

### Examples

```python
# Correct usage
// @PLACEHOLDER: Implement volume-weighted SMA calculation, TSD-15
def volume_weighted_sma(prices, volumes, period):
    pass

# With additional context
// @PLACEHOLDER: Complete IBKR options data integration, REQ-023
# TODO: Add support for complex options strategies
def get_options_chain(symbol):
    raise NotImplementedError("Options chain retrieval pending")
```

## Requirements

### 1. Mandatory Fields
- **Description**: Clear explanation of missing functionality
- **Requirement ID**: Traceable to specification (REQ-XXX, FRD-XXX, TSD-XXX)

### 2. Placement Rules
- Place immediately before incomplete function/class/method
- Use single-line comments in the target language
- Include context if the placeholder is not self-explanatory

### 3. Prohibited Patterns
```python
# ❌ Invalid - no requirement ID
// @PLACEHOLDER: Fix this later

# ❌ Invalid - vague description  
// @PLACEHOLDER: TODO, REQ-001

# ❌ Invalid - wrong format
# TODO: Implement this - REQ-123
```

## Automated Processing

### 1. GitHub Actions Integration
The system automatically:
- Scans all code files for @PLACEHOLDER tags
- Creates GitHub Issues for each placeholder group
- Fails builds on main branch if placeholders exist
- Generates reports for tracking

### 2. Issue Creation
Placeholders are grouped by requirement ID:

```yaml
Title: "[PLACEHOLDER] REQ-023: Technical Debt Resolution"
Labels: ["Technical-Debt", "Placeholder", "Phase-X"]
Assignees: [automatic based on file ownership]
```

### 3. Build Gates
- **Pull Requests**: Warning but not blocking
- **Main Branch**: Blocking gate prevents merges
- **Release Branches**: Strict blocking

## Resolution Process

### 1. Implementation Phase
```python
# Before resolution
// @PLACEHOLDER: Implement VW-SMA calculation, TSD-15
def volume_weighted_sma(prices, volumes, period):
    pass

# After resolution
def volume_weighted_sma(prices, volumes, period):
    """
    Calculate Volume-Weighted Simple Moving Average.
    
    Args:
        prices: Price series
        volumes: Volume series  
        period: Calculation period
        
    Returns:
        VW-SMA values
    """
    vw_prices = prices * volumes
    return vw_prices.rolling(period).sum() / volumes.rolling(period).sum()
```

### 2. Testing Requirements
- Add unit tests for resolved functionality
- Update integration tests if applicable
- Verify no regressions introduced

### 3. Documentation Updates
- Update technical documentation
- Add API documentation if applicable
- Update requirements traceability

## Deferral Process

### 1. Acceptable Deferrals
Some placeholders may be deferred to future phases:
- Non-critical functionality for current phase
- Dependencies on external systems not yet available
- Future enhancement features

### 2. Deferral Procedure
```python
// @PLACEHOLDER: Advanced portfolio optimization algorithms, REQ-045
// @DEFERRED: Phase 3 - pending advanced ML models integration
// @REASON: Current basic optimization sufficient for Phase 1-2 requirements
def advanced_portfolio_optimization():
    # Use basic optimization for now
    return basic_portfolio_optimization()
```

### 3. Approval Requirements
- Technical lead approval required
- Document business justification
- Update project timeline if necessary

## Quality Assurance

### 1. Code Review Checklist
- [ ] All placeholders have requirement IDs
- [ ] Descriptions are clear and actionable
- [ ] No placeholder in production-critical paths
- [ ] Temporary workarounds are documented

### 2. Phase Completion Gates
Before phase completion:
- [ ] All placeholders resolved or formally deferred
- [ ] GitHub issues closed or moved to future phases
- [ ] No blocking placeholders remain

### 3. Metrics and Reporting
- **Placeholder Density**: Placeholders per 1000 lines of code
- **Resolution Rate**: Placeholders resolved per sprint
- **Technical Debt Score**: Weighted by requirement criticality

## Best Practices

### 1. Writing Good Placeholders
```python
# ✅ Good - specific and actionable
// @PLACEHOLDER: Implement Greeks calculation for options pricing, REQ-089
def calculate_greeks(option_data):
    pass

# ✅ Good - includes constraint information
// @PLACEHOLDER: Add latency optimization (<1ms target), PERF-003
def process_market_data(data):
    # Current implementation ~5ms, needs optimization
    return slow_processing(data)
```

### 2. Temporary Implementations
```python
// @PLACEHOLDER: Replace with production ML model, AI-012
def predict_price_movement(data):
    # Temporary: Use simple moving average
    # Production: Deploy trained LSTM model
    return simple_moving_average_prediction(data)
```

### 3. Integration Points
```python
// @PLACEHOLDER: Complete IBKR paper trading integration, BROKER-005
class IBKRAdapter:
    def __init__(self):
        # Mock implementation for development
        self.mock_mode = True
        
    def place_order(self, order):
        if self.mock_mode:
            return self._mock_order_placement(order)
        # Real implementation pending
        raise NotImplementedError()
```

## Tooling Support

### 1. IDE Integration
- VS Code extension for placeholder validation
- Syntax highlighting for placeholder comments
- Quick actions for creating GitHub issues

### 2. Git Hooks
```bash
#!/bin/sh
# Pre-commit hook to validate placeholders
python scripts/validate_placeholders.py
```

### 3. CI/CD Integration
```yaml
- name: Scan for Placeholders
  run: python .github/scripts/scan_placeholders.py
  if: github.ref == 'refs/heads/main'
```

## Compliance and Audit

### 1. Regulatory Requirements
- Complete audit trail of all placeholders
- Traceability to business requirements
- Evidence of systematic resolution

### 2. Documentation Requirements
- Placeholder register with status tracking
- Risk assessment for deferred items
- Approval records for deferrals

### 3. Reporting
- Weekly placeholder status reports
- Phase completion certification
- Technical debt trend analysis

## Troubleshooting

### Common Issues
1. **False Positives**: Comments containing "@PLACEHOLDER" in documentation
2. **Missing Requirements**: Placeholders without traceable IDs
3. **Build Failures**: Unexpected placeholder detection

### Solutions
```python
# Exclude from scanning
# This documentation mentions @PLACEHOLDER but is not a real placeholder

# Use escape in documentation
# The format is /​/ @​PLACEHOLDER: description, req_id
```

This protocol ensures systematic management of incomplete implementations while maintaining development velocity and code quality.