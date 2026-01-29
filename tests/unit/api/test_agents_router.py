"""Tests for the agents router."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from src.api.main import app


client = TestClient(app)


@patch("src.api.routers.agents.AgentManager")
def test_list_agents(mock_manager_class):
    """Test listing agents."""
    mock_manager = MagicMock()
    mock_manager_class.return_value = mock_manager
    mock_manager.list_agents.return_value = [
        {"name": "RETAIL001-CustomerSupport-AG001", "id": "agent-123", "version": 1, "model": "gpt-4"},
        {"name": "RETAIL001-CustomerSupport-AG002", "id": "agent-456", "version": 1, "model": "gpt-4"},
    ]

    response = client.get("/api/agents")
    assert response.status_code == 200
    data = response.json()

    assert "agents" in data
    assert "count" in data
    assert data["count"] == 2
    assert len(data["agents"]) == 2
    assert data["agents"][0]["name"] == "RETAIL001-CustomerSupport-AG001"


@patch("src.api.routers.agents.AgentManager")
def test_list_agents_empty(mock_manager_class):
    """Test listing agents when none exist."""
    mock_manager = MagicMock()
    mock_manager_class.return_value = mock_manager
    mock_manager.list_agents.return_value = []

    response = client.get("/api/agents")
    assert response.status_code == 200
    data = response.json()

    assert data["count"] == 0
    assert len(data["agents"]) == 0


@patch("src.api.routers.agents.AgentManager")
def test_delete_agent(mock_manager_class):
    """Test deleting a specific agent."""
    mock_manager = MagicMock()
    mock_manager_class.return_value = mock_manager
    mock_manager.delete_agent.return_value = True

    response = client.delete("/api/agents/test-agent")
    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    mock_manager.delete_agent.assert_called_once_with("test-agent")


@patch("src.api.routers.agents.AgentManager")
def test_delete_agent_not_found(mock_manager_class):
    """Test deleting non-existent agent."""
    mock_manager = MagicMock()
    mock_manager_class.return_value = mock_manager
    mock_manager.delete_agent.return_value = False

    response = client.delete("/api/agents/nonexistent-agent")
    assert response.status_code == 404


@patch("src.api.routers.agents.AgentManager")
def test_delete_all_agents(mock_manager_class):
    """Test deleting all agents."""
    mock_manager = MagicMock()
    mock_manager_class.return_value = mock_manager
    mock_manager.delete_all_agents.return_value = {
        "deleted": [{"name": "agent1"}, {"name": "agent2"}],
        "failed": [],
        "total": 2,
        "deleted_count": 2,
        "failed_count": 0,
    }

    response = client.delete("/api/agents")
    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert data["deleted_count"] == 2
    assert data["failed_count"] == 0


def test_get_creation_progress():
    """Test getting agent creation progress."""
    response = client.get("/api/agents/progress")
    assert response.status_code == 200
    data = response.json()

    assert "running" in data
    assert "current" in data
    assert "total" in data
    assert "message" in data
