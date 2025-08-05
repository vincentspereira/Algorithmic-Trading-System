# Integration Tests

This directory contains integration tests for various system components.

## Test Categories

- **Risk Management Tests**: VaR engine, portfolio optimization, stress testing
- **Order Management Tests**: Order lifecycle, execution, management
- **API Tests**: GraphQL API, REST API endpoints
- **System Tests**: Phase structure validation, component integration

## Running Tests

```bash
# Run all integration tests
python -m pytest tests/integration/

# Run specific test category
python -m pytest tests/integration/test_risk_management/
python -m pytest tests/integration/test_order_management/
```

## Test Structure

Each test file follows the naming convention `test_<component>_<type>.py` and includes:
- Setup and teardown procedures
- Component initialization tests
- Functionality validation
- Error handling verification