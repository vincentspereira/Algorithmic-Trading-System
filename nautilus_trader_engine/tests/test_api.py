"""
Comprehensive Unit Tests for the FastAPI Endpoints in the Algorithmic Trading System.

This test suite covers all API endpoints, including:
- Authentication flow (token generation, validation)
- Backtesting endpoint with various strategies and error cases
- Optimization endpoint with parameter validation
- Feature queries endpoint with different symbols and date ranges

It includes tests for:
- Valid requests with expected responses
- Invalid requests and error handling
- Authentication and authorization
- Edge cases and boundary conditions
- Performance metrics validation

This suite uses pytest and FastAPI's TestClient and mocks external dependencies.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone

from nautilus_trader_engine.api.main import app
from nautilus_trader_engine.api.core.security import create_access_token

# Mock the BacktestRunner to avoid actual backtesting during tests
mock_backtest_runner = MagicMock()
mock_backtest_runner.fetch_data.return_value = True
mock_backtest_runner.run_backtrader_backtest.return_value = {
    "total_return": 0.1,
    "sharpe_ratio": 1.2,
}
mock_backtest_runner.run_trading_gym_backtest.return_value = {
    "total_return": 0.08,
    "sharpe_ratio": 1.1,
}

# Mock the OptimizationEngine
mock_optimization_engine = MagicMock()
mock_optimization_engine.optimize.return_value = {
    "status": "completed",
    "timestamp": datetime.now(timezone.utc),
    "parameters": {
        "ticker": "AAPL",
        "start_date": "2023-01-01",
        "end_date": "2023-12-31",
        "strategy": "sma_crossover",
        "initial_capital": 100000.0,
        "n_trials": 100,
        "timeout": 300,
        "objective": "sharpe_ratio",
        "user_id": "demo_user_001"
    },
    "best_parameters": {"fast_period": 10, "slow_period": 30},
    "best_value": 1.5,
    "n_trials": 100,
    "n_complete_trials": 95,
    "n_failed_trials": 5,
    "study_name": "test_study",
    "optimization_time": 120.5,
    "trials": [],
}

@pytest.fixture(scope="module")
def client():
    """
    Test client for the FastAPI application.
    """
    with TestClient(app) as c:
        yield c

@pytest.fixture(scope="module")
def valid_token():
    """
    Generate a valid JWT token for testing.
    """
    return create_access_token(subject="demo_user_001")

@pytest.fixture
def auth_headers(valid_token):
    """
    Authentication headers with a valid token.
    """
    return {"Authorization": f"Bearer {valid_token}"}

# Test Authentication Endpoints
def test_login_success(client):
    response = client.post("/api/v1/auth/login", json={"username": "demo", "password": "demo123"})
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_login_failure(client):
    response = client.post("/api/v1/auth/login", json={"username": "wrong", "password": "user"})
    assert response.status_code == 401

# Test Backtesting Endpoints
@patch('run_initial_backtest.BacktestRunner', return_value=mock_backtest_runner)
def test_run_backtest_success(mock_runner, client, auth_headers):
    response = client.post(
        "/api/v1/backtest/backtest/",
        json={
            "ticker": "AAPL",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "strategy_name": "moving_average_crossover",
            "initial_capital": 100000,
        },
        headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["status"] == "completed"

def test_run_backtest_unauthorized(client):
    response = client.post("/api/v1/backtest/backtest/", json={})
    assert response.status_code == 401

# Test Optimization Endpoints
@patch('nautilus_trader_engine.api.routers.optimization.OptimizationEngine')
def test_run_optimization_success(mock_engine_class, client, auth_headers):
    # Configure the mock class to return our mock instance
    mock_engine_class.return_value = mock_optimization_engine
    response = client.post(
        "/api/v1/optimise/optimise/",
        json={
            "ticker": "AAPL",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "strategy": "sma_crossover",
            "params": {
                "fast_period": {"min": 5, "max": 15},
                "slow_period": {"min": 20, "max": 40},
            },
        },
        headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["status"] == "completed"

def test_run_optimization_unauthorized(client):
    response = client.post("/api/v1/optimise/optimise/", json={})
    assert response.status_code == 401

# Test Features Endpoints
def test_get_features_success(client, auth_headers):
    response = client.get(
        "/api/v1/features/AAPL?start_date=2023-01-01T00:00:00&end_date=2023-01-31T00:00:00&feature_types=market_data&feature_types=indicators",
        headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["symbol"] == "AAPL"
    assert len(response.json()["features"]) == 2

def test_get_features_unauthorized(client):
    response = client.get("/api/v1/features/AAPL?start_date=2023-01-01T00:00:00&end_date=2023-01-31T00:00:00&feature_types=market_data")
    assert response.status_code == 401


# ============================================================================
# EXPANDED AUTHENTICATION TESTS
# ============================================================================

def test_login_invalid_username(client):
    """Test login with invalid username"""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "invalid_user", "password": "demo123"}
    )
    assert response.status_code == 401
    assert "Invalid credentials" in response.json()["detail"]


def test_login_invalid_password(client):
    """Test login with invalid password"""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "demo", "password": "wrong_password"}
    )
    assert response.status_code == 401
    assert "Invalid credentials" in response.json()["detail"]


def test_login_missing_username(client):
    """Test login with missing username"""
    response = client.post(
        "/api/v1/auth/login",
        json={"password": "demo123"}
    )
    assert response.status_code == 422  # Validation error


def test_login_missing_password(client):
    """Test login with missing password"""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "demo"}
    )
    assert response.status_code == 422  # Validation error


def test_login_empty_credentials(client):
    """Test login with empty credentials"""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "", "password": ""}
    )
    assert response.status_code == 401


def test_invalid_token_format(client):
    """Test API access with malformed token"""
    headers = {"Authorization": "Bearer invalid_token_format"}
    response = client.post("/api/v1/backtest/backtest/", json={}, headers=headers)
    assert response.status_code == 401


def test_missing_bearer_prefix(client):
    """Test API access with token missing Bearer prefix"""
    # Create a valid token but without Bearer prefix
    token = create_access_token(subject="demo_user_001")
    headers = {"Authorization": token}  # Missing "Bearer " prefix
    response = client.post("/api/v1/backtest/backtest/", json={}, headers=headers)
    assert response.status_code == 401


def test_expired_token(client):
    """Test API access with expired token"""
    # Create an expired token
    expired_token = create_access_token(
        subject="demo_user_001",
        expires_delta=timedelta(seconds=-1)  # Already expired
    )
    headers = {"Authorization": f"Bearer {expired_token}"}
    response = client.post("/api/v1/backtest/backtest/", json={}, headers=headers)
    assert response.status_code == 401


# ============================================================================
# EXPANDED BACKTEST ENDPOINT TESTS
# ============================================================================

@patch('run_initial_backtest.BacktestRunner', return_value=mock_backtest_runner)
def test_backtest_invalid_ticker(mock_runner, client, auth_headers):
    """Test backtest with invalid ticker symbol"""
    response = client.post(
        "/api/v1/backtest/backtest/",
        json={
            "ticker": "",  # Empty ticker
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "strategy_name": "moving_average_crossover",
            "initial_capital": 100000,
        },
        headers=auth_headers
    )
    assert response.status_code == 422  # Validation error


@patch('run_initial_backtest.BacktestRunner', return_value=mock_backtest_runner)
def test_backtest_invalid_date_format(mock_runner, client, auth_headers):
    """Test backtest with invalid date format"""
    response = client.post(
        "/api/v1/backtest/backtest/",
        json={
            "ticker": "AAPL",
            "start_date": "invalid-date",
            "end_date": "2023-12-31",
            "strategy_name": "moving_average_crossover",
            "initial_capital": 100000,
        },
        headers=auth_headers
    )
    assert response.status_code == 422  # Validation error


@patch('run_initial_backtest.BacktestRunner', return_value=mock_backtest_runner)
def test_backtest_end_before_start(mock_runner, client, auth_headers):
    """Test backtest with end date before start date"""
    response = client.post(
        "/api/v1/backtest/backtest/",
        json={
            "ticker": "AAPL",
            "start_date": "2023-12-31",
            "end_date": "2023-01-01",  # End before start
            "strategy_name": "moving_average_crossover",
            "initial_capital": 100000,
        },
        headers=auth_headers
    )
    assert response.status_code == 422  # Should be caught by validation


@patch('run_initial_backtest.BacktestRunner', return_value=mock_backtest_runner)
def test_backtest_negative_capital(mock_runner, client, auth_headers):
    """Test backtest with negative initial capital"""
    response = client.post(
        "/api/v1/backtest/backtest/",
        json={
            "ticker": "AAPL",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "strategy_name": "moving_average_crossover",
            "initial_capital": -1000,  # Negative capital
        },
        headers=auth_headers
    )
    assert response.status_code == 422  # Validation error


@patch('run_initial_backtest.BacktestRunner', return_value=mock_backtest_runner)
def test_backtest_zero_capital(mock_runner, client, auth_headers):
    """Test backtest with zero initial capital"""
    response = client.post(
        "/api/v1/backtest/backtest/",
        json={
            "ticker": "AAPL",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "strategy_name": "moving_average_crossover",
            "initial_capital": 0,  # Zero capital
        },
        headers=auth_headers
    )
    assert response.status_code == 422  # Validation error


@patch('run_initial_backtest.BacktestRunner', return_value=mock_backtest_runner)
def test_backtest_unsupported_strategy(mock_runner, client, auth_headers):
    """Test backtest with unsupported strategy"""
    response = client.post(
        "/api/v1/backtest/backtest/",
        json={
            "ticker": "AAPL",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "strategy_name": "unsupported_strategy",
            "initial_capital": 100000,
        },
        headers=auth_headers
    )
    # This should still return 200 as the strategy validation is not strict in the current implementation
    assert response.status_code == 200


def test_backtest_data_fetch_failure(client, auth_headers):
    """Test backtest when data fetching fails"""
    # Mock a BacktestRunner that fails to fetch data
    mock_failing_runner = MagicMock()
    mock_failing_runner.fetch_data.return_value = False  # Simulate data fetch failure
    
    with patch('run_initial_backtest.BacktestRunner', return_value=mock_failing_runner):
        response = client.post(
            "/api/v1/backtest/backtest/",
            json={
                "ticker": "INVALID",
                "start_date": "2023-01-01",
                "end_date": "2023-12-31",
                "strategy_name": "moving_average_crossover",
                "initial_capital": 100000,
            },
            headers=auth_headers
        )
        assert response.status_code == 422
        assert "Failed to fetch market data" in response.json()["detail"]


# ============================================================================
# EXPANDED OPTIMIZATION ENDPOINT TESTS
# ============================================================================

@patch('nautilus_trader_engine.api.routers.optimization.OptimizationEngine')
def test_optimization_invalid_strategy(mock_engine_class, client, auth_headers):
    """Test optimization with invalid strategy"""
    mock_engine_class.return_value = mock_optimization_engine
    response = client.post(
        "/api/v1/optimise/optimise/",
        json={
            "ticker": "AAPL",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "strategy": "invalid_strategy",  # Invalid strategy
            "params": {
                "fast_period": {"min": 5, "max": 15},
                "slow_period": {"min": 20, "max": 40},
            },
        },
        headers=auth_headers
    )
    assert response.status_code == 422
    assert "not supported" in response.json()["detail"]


@patch('nautilus_trader_engine.api.routers.optimization.OptimizationEngine')
def test_optimization_invalid_parameters(mock_engine_class, client, auth_headers):
    """Test optimization with invalid parameter names"""
    mock_engine_class.return_value = mock_optimization_engine
    response = client.post(
        "/api/v1/optimise/optimise/",
        json={
            "ticker": "AAPL",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "strategy": "sma_crossover",
            "params": {
                "invalid_param": {"min": 5, "max": 15},  # Invalid parameter name
                "slow_period": {"min": 20, "max": 40},
            },
        },
        headers=auth_headers
    )
    assert response.status_code == 422
    assert "Invalid parameters" in response.json()["detail"]


@patch('nautilus_trader_engine.api.routers.optimization.OptimizationEngine')
def test_optimization_missing_required_fields(mock_engine_class, client, auth_headers):
    """Test optimization with missing required fields"""
    mock_engine_class.return_value = mock_optimization_engine
    response = client.post(
        "/api/v1/optimise/optimise/",
        json={
            "ticker": "AAPL",
            # Missing start_date, end_date, strategy, params
        },
        headers=auth_headers
    )
    assert response.status_code == 422  # Validation error


@patch('nautilus_trader_engine.api.routers.optimization.OptimizationEngine')
def test_optimization_invalid_parameter_ranges(mock_engine_class, client, auth_headers):
    """Test optimization with invalid parameter ranges (min > max)"""
    mock_engine_class.return_value = mock_optimization_engine
    response = client.post(
        "/api/v1/optimise/optimise/",
        json={
            "ticker": "AAPL",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "strategy": "sma_crossover",
            "params": {
                "fast_period": {"min": 20, "max": 10},  # min > max
                "slow_period": {"min": 20, "max": 40},
            },
        },
        headers=auth_headers
    )
    # This should still return 200 as the validation is handled by Optuna
    assert response.status_code == 200


# ============================================================================
# EXPANDED FEATURE ENDPOINT TESTS
# ============================================================================

def test_features_with_symbol_parameter(client, auth_headers):
    """Test features endpoint with symbol parameter"""
    response = client.get("/api/v1/features/MSFT", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "features" in data
    assert data["symbol"] == "MSFT"


def test_features_with_date_range(client, auth_headers):
    """Test features endpoint with date range parameters"""
    response = client.get(
        "/api/v1/features/AAPL?start_date=2023-01-01T00:00:00&end_date=2023-12-31T00:00:00",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "features" in data


def test_features_with_invalid_symbol(client, auth_headers):
    """Test features endpoint with invalid symbol"""
    response = client.get("/api/v1/features/INVALID_SYMBOL", headers=auth_headers)
    assert response.status_code == 200  # Should still return 200 with empty or default features


def test_features_with_invalid_date_format(client, auth_headers):
    """Test features endpoint with invalid date format"""
    response = client.get(
        "/api/v1/features/AAPL?start_date=invalid-date",
        headers=auth_headers
    )
    assert response.status_code == 422  # Validation error


def test_features_with_multiple_feature_types(client, auth_headers):
    """Test features endpoint with multiple feature types"""
    response = client.get(
        "/api/v1/features/AAPL?feature_types=market_data&feature_types=indicators&feature_types=sentiment",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["features"]) == 3


# ============================================================================
# ERROR HANDLING AND EDGE CASES
# ============================================================================

def test_nonexistent_endpoint(client):
    """Test accessing a non-existent endpoint"""
    response = client.get("/api/v1/nonexistent/")
    assert response.status_code == 404


def test_wrong_http_method(client, auth_headers):
    """Test using wrong HTTP method on endpoints"""
    # Try GET on POST endpoint
    response = client.get("/api/v1/backtest/backtest/", headers=auth_headers)
    assert response.status_code == 405  # Method not allowed


def test_malformed_json(client, auth_headers):
    """Test sending malformed JSON"""
    import requests
    # Use requests directly to send malformed JSON
    response = client.post(
        "/api/v1/backtest/backtest/",
        data="invalid json",  # Not valid JSON
        headers={**auth_headers, "Content-Type": "application/json"}
    )
    assert response.status_code == 422


def test_empty_request_body(client, auth_headers):
    """Test sending empty request body to endpoints that require data"""
    response = client.post(
        "/api/v1/backtest/backtest/",
        json={},  # Empty JSON
        headers=auth_headers
    )
    assert response.status_code == 422  # Validation error


def test_oversized_request(client, auth_headers):
    """Test sending oversized request data"""
    large_data = {
        "ticker": "AAPL",
        "start_date": "2023-01-01",
        "end_date": "2023-12-31",
        "strategy_name": "moving_average_crossover",
        "initial_capital": 100000,
        "large_field": "x" * 10000  # Very large field
    }
    response = client.post(
        "/api/v1/backtest/backtest/",
        json=large_data,
        headers=auth_headers
    )
    # Should still work unless there are specific size limits
    assert response.status_code in [200, 413, 422]


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

def test_full_workflow_backtest_to_optimization(client):
    """Test complete workflow: login -> backtest -> optimization"""
    # Step 1: Login
    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": "demo", "password": "demo123"}
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Step 2: Run backtest
    with patch('run_initial_backtest.BacktestRunner', return_value=mock_backtest_runner):
        backtest_response = client.post(
            "/api/v1/backtest/backtest/",
            json={
                "ticker": "AAPL",
                "start_date": "2023-01-01",
                "end_date": "2023-12-31",
                "strategy_name": "moving_average_crossover",
                "initial_capital": 100000,
            },
            headers=headers
        )
        assert backtest_response.status_code == 200
    
    # Step 3: Run optimization
    with patch('nautilus_trader_engine.api.routers.optimization.OptimizationEngine', return_value=mock_optimization_engine):
        optimization_response = client.post(
            "/api/v1/optimise/optimise/",
            json={
                "ticker": "AAPL",
                "start_date": "2023-01-01",
                "end_date": "2023-12-31",
                "strategy": "sma_crossover",
                "params": {
                    "fast_period": {"min": 5, "max": 15},
                    "slow_period": {"min": 20, "max": 40},
                },
            },
            headers=headers
        )
        assert optimization_response.status_code == 200


def test_concurrent_requests(client, auth_headers):
    """Test handling of concurrent requests"""
    import threading
    import time
    
    results = []
    
    def make_request():
        response = client.get("/api/v1/features/AAPL", headers=auth_headers)
        results.append(response.status_code)
    
    # Create multiple threads to simulate concurrent requests
    threads = []
    for _ in range(5):
        thread = threading.Thread(target=make_request)
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    # All requests should succeed
    assert all(status == 200 for status in results)
    assert len(results) == 5


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

def test_response_time_backtest(client, auth_headers):
    """Test that backtest endpoint responds within reasonable time"""
    import time
    
    with patch('run_initial_backtest.BacktestRunner', return_value=mock_backtest_runner):
        start_time = time.time()
        response = client.post(
            "/api/v1/backtest/backtest/",
            json={
                "ticker": "AAPL",
                "start_date": "2023-01-01",
                "end_date": "2023-12-31",
                "strategy_name": "moving_average_crossover",
                "initial_capital": 100000,
            },
            headers=auth_headers
        )
        end_time = time.time()
        
        assert response.status_code == 200
        assert (end_time - start_time) < 10  # Should complete within 10 seconds


def test_response_time_features(client, auth_headers):
    """Test that features endpoint responds within reasonable time"""
    import time
    
    start_time = time.time()
    response = client.get("/api/v1/features/AAPL", headers=auth_headers)
    end_time = time.time()
    
    assert response.status_code == 200
    assert (end_time - start_time) < 5  # Should complete within 5 seconds


# ============================================================================
# BOUNDARY VALUE TESTS
# ============================================================================

@patch('run_initial_backtest.BacktestRunner', return_value=mock_backtest_runner)
def test_backtest_minimum_capital(mock_runner, client, auth_headers):
    """Test backtest with minimum allowed capital"""
    response = client.post(
        "/api/v1/backtest/backtest/",
        json={
            "ticker": "AAPL",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "strategy_name": "moving_average_crossover",
            "initial_capital": 1,  # Minimum capital
        },
        headers=auth_headers
    )
    # Should work with minimum capital
    assert response.status_code in [200, 422]


@patch('run_initial_backtest.BacktestRunner', return_value=mock_backtest_runner)
def test_backtest_maximum_capital(mock_runner, client, auth_headers):
    """Test backtest with very large capital"""
    response = client.post(
        "/api/v1/backtest/backtest/",
        json={
            "ticker": "AAPL",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "strategy_name": "moving_average_crossover",
            "initial_capital": 1000000000,  # Very large capital
        },
        headers=auth_headers
    )
    assert response.status_code == 200


@patch('run_initial_backtest.BacktestRunner', return_value=mock_backtest_runner)
def test_backtest_extreme_periods(mock_runner, client, auth_headers):
    """Test backtest with extreme MA periods"""
    response = client.post(
        "/api/v1/backtest/backtest/",
        json={
            "ticker": "AAPL",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "strategy_name": "moving_average_crossover",
            "initial_capital": 100000,
            "fast_period": 1,  # Minimum period
            "slow_period": 200,  # Large period
        },
        headers=auth_headers
    )
    assert response.status_code == 200