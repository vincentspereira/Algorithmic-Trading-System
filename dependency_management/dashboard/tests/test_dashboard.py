"""
Test suite for dashboard service components.
"""

import asyncio
import json
from datetime import datetime, timedelta
import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
import redis
from unittest.mock import Mock, patch

from ..auth import (
    create_access_token,
    get_current_user,
    authenticate_user
)
from ..cache import DependencyCache
from ..error_handling import (
    RateLimiter,
    ErrorTracker,
    with_retry
)
from ..dashboard_service import DashboardService

# Fixtures
@pytest.fixture
def test_client():
    """Create test client"""
    from ..dashboard_service import app
    return TestClient(app)
    
@pytest.fixture
def redis_mock():
    """Mock Redis connection"""
    with patch('redis.Redis') as mock:
        yield mock
        
@pytest.fixture
def dependency_cache(redis_mock):
    """Create test cache instance"""
    return DependencyCache(
        host="localhost",
        port=6379,
        db=0
    )
    
@pytest.fixture
def error_tracker():
    """Create test error tracker"""
    return ErrorTracker()
    
# Auth Tests
def test_create_access_token():
    """Test JWT token creation"""
    data = {"sub": "testuser", "scopes": ["read"]}
    token = create_access_token(data)
    assert token is not None
    
@pytest.mark.asyncio
async def test_get_current_user():
    """Test current user retrieval"""
    token = create_access_token({"sub": "admin"})
    user = await get_current_user(
        security_scopes=Mock(scopes=["read"]),
        token=token
    )
    assert user.username == "admin"
    
def test_authenticate_user():
    """Test user authentication"""
    user = authenticate_user("admin", "admin")
    assert user is not None
    assert user.username == "admin"
    
    user = authenticate_user("admin", "wrong")
    assert user is None
    
# Cache Tests
def test_dependency_cache_set_get(redis_mock):
    """Test cache set/get operations"""
    cache = dependency_cache
    
    cache.set("test", "key", "value")
    redis_mock.set.assert_called_once()
    
    cache.get("test", "key")
    redis_mock.get.assert_called_once()
    
def test_historical_data_storage(redis_mock):
    """Test historical data operations"""
    cache = dependency_cache
    
    data = {"status": "healthy"}
    cache.store_historical_data("tier1", "dep1", data)
    redis_mock.zadd.assert_called_once()
    
    cache.get_historical_data("tier1", "dep1")
    redis_mock.zrangebyscore.assert_called_once()
    
# Error Handling Tests
@pytest.mark.asyncio
async def test_rate_limiter():
    """Test rate limiting"""
    limiter = RateLimiter(calls=2, period=1)
    
    async with limiter:
        assert len(limiter.calls_made) == 1
        
    async with limiter:
        assert len(limiter.calls_made) == 2
        
    with pytest.raises(RateLimitError):
        async with limiter:
            pass
            
def test_error_tracker():
    """Test error tracking"""
    tracker = error_tracker
    
    tracker.record_error(
        "TestError",
        "Test message",
        {"context": "test"}
    )
    
    summary = tracker.get_error_summary()
    assert "TestError" in summary
    assert summary["TestError"]["count"] == 1
    
# API Tests
async def test_overview_endpoint(test_client):
    """Test overview endpoint"""
    token = create_access_token({"sub": "admin"})
    response = test_client.get(
        "/api/v1/overview",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    
async def test_dependencies_endpoint(test_client):
    """Test dependencies endpoint"""
    token = create_access_token({"sub": "admin"})
    response = test_client.get(
        "/api/v1/dependencies/tier1",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    
# Performance Tests
@pytest.mark.benchmark
def test_cache_performance(benchmark, dependency_cache):
    """Benchmark cache operations"""
    def cache_operation():
        dependency_cache.set("test", "key", "value")
        dependency_cache.get("test", "key")
        
    benchmark(cache_operation)
    
@pytest.mark.benchmark
def test_api_performance(benchmark, test_client):
    """Benchmark API endpoints"""
    token = create_access_token({"sub": "admin"})
    headers = {"Authorization": f"Bearer {token}"}
    
    def api_call():
        test_client.get("/api/v1/overview", headers=headers)
        
    benchmark(api_call)
    
# Integration Tests
@pytest.mark.integration
async def test_full_dependency_check():
    """Test complete dependency check flow"""
    service = DashboardService(
        config_path="test_config.json",
        github_token="test-token",
        nvd_api_key="test-key"
    )
    
    # Test monitoring
    results = await service.monitor.monitor_all()
    assert results is not None
    
    # Test caching
    cached = service.cache.get(
        "dependency_status",
        "test_dependency"
    )
    assert cached is not None
    
    # Test alerting
    alerts = await service.notification_manager.get_active_alerts()
    assert isinstance(alerts, list)
    
if __name__ == '__main__':
    pytest.main([__file__])
