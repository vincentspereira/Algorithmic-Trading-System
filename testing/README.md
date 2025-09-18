# Trading System Testing Framework

This directory contains a comprehensive testing framework for the algorithmic trading system, implementing multiple testing levels to ensure system reliability, performance, and correctness.

## Testing Architecture

### Testing Pyramid

```
    /\     UAT Tests (User Acceptance)
   /  \    
  /____\   System Tests (End-to-End)
 /______\  Integration Tests (API & Services)
/________\ Unit Tests (Components & Logic)
```

### Testing Levels

1. **Unit Tests** (`unit/`)
   - Test individual components in isolation
   - Fast execution (< 1 second per test)
   - High code coverage (>90%)
   - Mock external dependencies

2. **Integration Tests** (`integration/`)
   - Test service interactions
   - Database and external API integration
   - Message queue communication
   - Moderate execution time (1-10 seconds per test)

3. **System Tests** (`system/`)
   - End-to-end workflow testing
   - Complete trading scenarios
   - Cross-service communication
   - Longer execution time (10-60 seconds per test)

4. **User Acceptance Tests** (`uat/`)
   - Business scenario validation
   - User story verification
   - Compliance and regulatory testing
   - Real-world use case simulation

5. **Performance Tests** (`performance/`)
   - Load testing with Locust
   - Stress testing
   - Latency and throughput measurement
   - Scalability validation

## Directory Structure

```
testing/
├── pytest.ini                 # Pytest configuration
├── conftest.py                # Shared fixtures and utilities
├── requirements.txt           # Testing dependencies
├── README.md                  # This file
├── unit/                      # Unit tests
│   ├── __init__.py
│   ├── test_trading_engine.py
│   ├── test_portfolio_manager.py
│   ├── test_risk_manager.py
│   └── test_market_data.py
├── integration/               # Integration tests
│   ├── __init__.py
│   ├── test_api_endpoints.py
│   ├── test_database_integration.py
│   ├── test_kafka_messaging.py
│   └── test_external_apis.py
├── system/                    # System tests
│   ├── __init__.py
│   ├── test_trading_workflows.py
│   ├── test_portfolio_workflows.py
│   └── test_risk_workflows.py
├── uat/                       # User acceptance tests
│   ├── __init__.py
│   ├── test_user_acceptance.py
│   ├── test_compliance.py
│   └── test_business_scenarios.py
├── performance/               # Performance tests
│   ├── __init__.py
│   ├── locustfile.py
│   ├── stress_tests.py
│   └── benchmark_tests.py
└── reports/                   # Test reports and artifacts
    ├── coverage/
    ├── performance/
    └── screenshots/
```

## Quick Start

### Prerequisites

```bash
# Install testing dependencies
pip install -r testing/requirements.txt

# Set up test environment variables
export TESTING_ENV=true
export DATABASE_URL=postgresql://test_user:test_pass@localhost:5432/test_db
export REDIS_URL=redis://localhost:6379/1
export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
```

### Running Tests

#### All Tests
```bash
# Run all tests with coverage
pytest testing/ --cov=src --cov-report=html --cov-report=term
```

#### By Test Level
```bash
# Unit tests only
pytest testing/unit/ -v

# Integration tests only
pytest testing/integration/ -v

# System tests only
pytest testing/system/ -v

# UAT tests only
pytest testing/uat/ -v
```

#### By Component
```bash
# Trading engine tests
pytest testing/ -k "trading_engine" -v

# Portfolio manager tests
pytest testing/ -k "portfolio" -v

# Risk manager tests
pytest testing/ -k "risk" -v
```

#### Performance Tests
```bash
# Run load tests with Locust
cd testing/performance
locust -f locustfile.py --host=http://localhost:8000

# Headless performance test
locust -f locustfile.py --host=http://localhost:8000 --users=100 --spawn-rate=10 --run-time=5m --headless
```

### Test Markers

Tests are organized using pytest markers:

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.system` - System tests
- `@pytest.mark.uat` - User acceptance tests
- `@pytest.mark.performance` - Performance tests
- `@pytest.mark.slow` - Slow-running tests
- `@pytest.mark.external` - Tests requiring external services
- `@pytest.mark.security` - Security-related tests
- `@pytest.mark.compliance` - Compliance tests

#### Running by Marker
```bash
# Run only fast tests
pytest -m "not slow" -v

# Run only security tests
pytest -m "security" -v

# Run integration and system tests
pytest -m "integration or system" -v
```

## Test Configuration

### Environment Setup

The testing framework uses different configurations for different environments:

- **Local Development**: Uses local services (Docker Compose)
- **CI/CD Pipeline**: Uses containerized services
- **Staging**: Uses staging environment services
- **Production**: Read-only tests only

### Database Testing

- Uses PostgreSQL test database with transaction rollback
- Each test runs in isolation with clean state
- Database fixtures provide consistent test data
- Supports both in-memory and persistent test databases

### Message Queue Testing

- Uses dedicated Kafka test topics
- Automatic cleanup after test completion
- Mock producers and consumers for unit tests
- Real Kafka integration for system tests

### External API Testing

- Uses VCR.py for HTTP interaction recording/playback
- Mock external services for unit/integration tests
- Rate limiting and error simulation
- Sandbox environments for system tests

## Test Data Management

### Fixtures

Common fixtures are defined in `conftest.py`:

- `db_session` - Database session with rollback
- `redis_client` - Redis client for caching tests
- `kafka_producer` - Kafka producer for messaging tests
- `mock_market_data` - Simulated market data
- `test_user` - Test user with authentication
- `test_portfolio` - Sample portfolio data

### Test Data

```python
# Using fixtures in tests
def test_portfolio_creation(db_session, test_user):
    portfolio = create_portfolio(user_id=test_user.id)
    assert portfolio.user_id == test_user.id

# Parameterized tests
@pytest.mark.parametrize("symbol,expected_price", [
    ("AAPL", 150.0),
    ("GOOGL", 2500.0),
    ("MSFT", 300.0)
])
def test_price_validation(symbol, expected_price):
    assert validate_price(symbol, expected_price)
```

## Continuous Integration

### GitHub Actions Workflow

The CI/CD pipeline runs tests in the following order:

1. **Code Quality Checks**
   - Linting (flake8, black, isort)
   - Type checking (mypy)
   - Security scanning (bandit, safety)

2. **Unit Tests**
   - Fast execution
   - High parallelization
   - Code coverage reporting

3. **Integration Tests**
   - Service dependencies
   - Database migrations
   - API contract testing

4. **System Tests**
   - End-to-end workflows
   - Cross-service integration
   - Performance benchmarks

5. **UAT Tests**
   - Business scenario validation
   - Compliance verification
   - User story acceptance

### Test Reports

Test results are automatically generated and stored:

- **Coverage Reports**: HTML and XML formats
- **Test Results**: JUnit XML for CI integration
- **Performance Reports**: Locust HTML reports
- **Screenshots**: For UI test failures

## Best Practices

### Writing Tests

1. **Follow AAA Pattern**
   ```python
   def test_order_creation():
       # Arrange
       user = create_test_user()
       symbol = "AAPL"
       
       # Act
       order = create_order(user.id, symbol, "BUY", 100)
       
       # Assert
       assert order.symbol == symbol
       assert order.side == "BUY"
       assert order.quantity == 100
   ```

2. **Use Descriptive Names**
   ```python
   # Good
   def test_portfolio_rebalancing_with_risk_constraints():
       pass
   
   # Bad
   def test_rebalance():
       pass
   ```

3. **Test Edge Cases**
   ```python
   @pytest.mark.parametrize("quantity,expected_error", [
       (0, "Quantity must be positive"),
       (-1, "Quantity must be positive"),
       (None, "Quantity is required")
   ])
   def test_invalid_order_quantities(quantity, expected_error):
       with pytest.raises(ValidationError, match=expected_error):
           create_order("AAPL", "BUY", quantity)
   ```

4. **Mock External Dependencies**
   ```python
   @patch('src.services.market_data.get_quote')
   def test_order_pricing(mock_get_quote):
       mock_get_quote.return_value = {"price": 150.0}
       
       order = create_market_order("AAPL", "BUY", 100)
       
       assert order.estimated_price == 150.0
       mock_get_quote.assert_called_once_with("AAPL")
   ```

### Performance Testing

1. **Define Performance Criteria**
   - Response time < 100ms for API calls
   - Throughput > 1000 requests/second
   - 99th percentile latency < 500ms

2. **Test Realistic Scenarios**
   - Market open surge patterns
   - High-frequency trading loads
   - Concurrent user sessions

3. **Monitor Resource Usage**
   - CPU and memory consumption
   - Database connection pools
   - Message queue throughput

### Security Testing

1. **Authentication Tests**
   ```python
   def test_unauthorized_access_denied():
       response = client.get("/api/v1/portfolio")
       assert response.status_code == 401
   
   def test_invalid_token_rejected():
       headers = {"Authorization": "Bearer invalid_token"}
       response = client.get("/api/v1/portfolio", headers=headers)
       assert response.status_code == 401
   ```

2. **Input Validation Tests**
   ```python
   def test_sql_injection_prevention():
       malicious_input = "'; DROP TABLE users; --"
       response = client.get(f"/api/v1/users/{malicious_input}")
       assert response.status_code == 400
   ```

3. **Data Privacy Tests**
   ```python
   def test_user_data_isolation():
       user1_data = get_portfolio(user1.id)
       user2_data = get_portfolio(user2.id)
       
       assert user1_data != user2_data
       assert user1.id not in str(user2_data)
   ```

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   ```bash
   # Check database status
   docker-compose ps postgres
   
   # Reset test database
   docker-compose exec postgres psql -U postgres -c "DROP DATABASE IF EXISTS test_db; CREATE DATABASE test_db;"
   ```

2. **Kafka Connection Issues**
   ```bash
   # Check Kafka status
   docker-compose ps kafka
   
   # List topics
   docker-compose exec kafka kafka-topics --list --bootstrap-server localhost:9092
   ```

3. **Redis Connection Problems**
   ```bash
   # Check Redis status
   docker-compose ps redis
   
   # Flush test data
   docker-compose exec redis redis-cli FLUSHDB
   ```

### Debug Mode

```bash
# Run tests with debug output
pytest testing/ -v -s --tb=long

# Run specific test with pdb
pytest testing/unit/test_trading_engine.py::test_order_creation -v -s --pdb

# Capture logs
pytest testing/ --log-cli-level=DEBUG
```

### Performance Debugging

```bash
# Profile test execution
pytest testing/ --profile

# Memory usage profiling
pytest testing/ --memray

# Generate flame graphs
py-spy record -o profile.svg -- pytest testing/
```

## Reporting and Metrics

### Coverage Reports

```bash
# Generate HTML coverage report
pytest testing/ --cov=src --cov-report=html
open htmlcov/index.html

# Coverage with branch analysis
pytest testing/ --cov=src --cov-branch --cov-report=term-missing
```

### Test Metrics

- **Test Execution Time**: Track test performance over time
- **Flaky Test Detection**: Identify unstable tests
- **Coverage Trends**: Monitor code coverage changes
- **Failure Analysis**: Categorize and track test failures

### Integration with Monitoring

- Test results are sent to monitoring systems
- Performance metrics are tracked in Grafana
- Alerts are configured for test failures
- Trend analysis for test suite health

## Contributing

### Adding New Tests

1. **Choose Appropriate Test Level**
   - Unit: Testing individual functions/classes
   - Integration: Testing service interactions
   - System: Testing complete workflows
   - UAT: Testing business scenarios

2. **Follow Naming Conventions**
   - Test files: `test_*.py`
   - Test functions: `test_*`
   - Test classes: `Test*`

3. **Add Appropriate Markers**
   ```python
   @pytest.mark.unit
   @pytest.mark.trading
   def test_order_validation():
       pass
   ```

4. **Update Documentation**
   - Add test descriptions
   - Update this README if needed
   - Document any new fixtures or utilities

### Code Review Checklist

- [ ] Tests follow AAA pattern
- [ ] Appropriate test level chosen
- [ ] Edge cases covered
- [ ] External dependencies mocked
- [ ] Descriptive test names
- [ ] Proper assertions used
- [ ] Test data cleanup handled
- [ ] Performance considerations addressed

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Locust Documentation](https://docs.locust.io/)
- [Testing Best Practices](https://docs.python-guide.org/writing/tests/)
- [CI/CD Pipeline Documentation](../.github/workflows/README.md)
- [System Architecture](../docs/architecture.md)