
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app

client = TestClient(app)

@patch('app.agents.main_agent.agent_executor')
@patch('app.agents.main_agent.get_or_create_memory')
def test_chat_with_assistant(mock_get_or_create_memory, mock_agent_executor):
    mock_agent_executor.invoke.return_value = {"output": "Hello from AI Assistant"}
    mock_memory = MagicMock()
    mock_get_or_create_memory.return_value = mock_memory

    response = client.post("/api/v1/chat", json={
        "message": "Hello",
        "session_id": "test_session"
    })

    assert response.status_code == 200
    assert response.json()["response"] == "Hello from AI Assistant"
    mock_agent_executor.invoke.assert_called_once()
    mock_memory.chat_memory.add_user_message.assert_called_once_with("Hello")
    mock_memory.chat_memory.add_ai_message.assert_called_once_with("Hello from AI Assistant")
