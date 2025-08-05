# Standalone Test Files

This directory contains standalone test files that can be run independently to test specific components of the Algorithmic Trading System.

## Test Categories

### 📈 Trading & Orders
- **test_order_direct.py** - Direct order testing
- **test_order_management_simple.py** - Order management system testing
- **test_order_minimal.py** - Minimal order functionality testing
- **test_order_simple.py** - Simple order testing
- **test_order_standalone.py** - Standalone order testing

### 🔄 Dynamic Systems
- **test_dynamic_hedging_simple.py** - Dynamic hedging system testing
- **test_portfolio_optimizer_simple.py** - Portfolio optimization testing
- **test_stress_testing_simple.py** - Stress testing functionality
- **test_var_simple.py** - Value at Risk (VaR) testing

### 🌐 API & Integration
- **test_graphql_api_simple.py** - Simple GraphQL API testing
- **test_graphql_comprehensive.py** - Comprehensive GraphQL testing
- **test_phase2_structure.py** - Phase 2 structure testing

## Usage

These test files are designed to be run independently without requiring the full system setup. They provide focused testing of specific components and can be useful for:

- **Development Testing** - Quick validation during development
- **Component Isolation** - Testing individual components in isolation
- **Debugging** - Focused testing when troubleshooting issues
- **Learning** - Understanding how specific components work

## Running Tests

Each test file can be run directly:

```bash
# Example: Run a specific test
python test_order_simple.py

# Or using pytest
pytest test_order_simple.py -v
```

## Test Structure

Most tests follow a similar structure:
1. **Setup** - Initialize required components
2. **Test Execution** - Run the specific functionality
3. **Validation** - Verify expected results
4. **Cleanup** - Clean up resources if needed

These tests provide a quick way to validate that specific components are working correctly without the overhead of running the full system test suite.