
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app

client = TestClient(app)

@patch('ai_assistant.config.config.requests.get')
def test_health_check(mock_requests_get):
    mock_requests_get.return_value.status_code = 200
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
