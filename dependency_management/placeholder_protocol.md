# Placeholder Protocol

This document describes the placeholder protocol used in the Algorithmic Trading System for tracking incomplete implementations.

## Purpose

The placeholder protocol is used to:
1. Identify incomplete functionality during development
2. Track missing features with requirement IDs
3. Create automated GitHub issues for follow-up work
4. Ensure proper review before phase completion

## Placeholder Format

All placeholders must follow this format:

```
// @PLACEHOLDER: [reason], [requirement ID]
```

### Components

1. **Reason**: Brief explanation of why the placeholder exists
   - Examples: "Implementation pending", "Requires further research", "Depends on upstream component"

2. **Requirement ID**: Reference to the specific requirement from the documentation
   - Examples: "REQ-001", "FRD-15", "TSD-23"

## Examples

### Python Code
```python
def calculate_risk_metrics(portfolio):
    # @PLACEHOLDER: Implementation pending, REQ-045
    pass
```

### JavaScript Code
```javascript
function renderDashboard() {
    // @PLACEHOLDER: Requires charting library integration, FRD-12
    console.log("Dashboard rendering not yet implemented");
}
```

### Configuration Files
```yaml
# @PLACEHOLDER: Need to configure production database settings, TSD-08
database:
  host: localhost
  port: 5432
```

## GitHub Issue Creation

When a placeholder is added to the codebase, an automated process should:
1. Scan for the `// @PLACEHOLDER:` tag
2. Extract the reason and requirement ID
3. Create a GitHub issue with:
   - Title: "[PLACEHOLDER] [requirement ID]: [brief description]"
   - Body: Full placeholder information with file path and line number
   - Labels: "Technical-Debt", "Placeholder"
   - Assignment: To the appropriate team or developer

## Phase-End Review Process

Before any phase can be completed, the following process must be executed:

1. **Automated Codebase Scan**:
   - Configure CI/CD pipeline to scan for `// @PLACEHOLDER:` tags
   - Fail the build if any placeholders are found
   - Generate a report of all placeholders found

2. **Manual Backlog Review**:
   - Review all tickets in the "Placeholder Review" backlog
   - For each ticket, either:
     - **Resolve**: Complete the work, update code, remove tag, close ticket
     - **Defer**: Move to a specific future phase with approval

A phase is only considered complete when:
- The automated scan passes (no placeholders found)
- The placeholder backlog for that phase is empty (all tickets resolved or formally deferred)