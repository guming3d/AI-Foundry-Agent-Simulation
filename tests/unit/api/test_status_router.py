"""Tests for the status router."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from src.api.main import app


client = TestClient(app)


def test_health_check():
    """Test the health check endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_root_endpoint():
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data
    assert data["name"] == "Microsoft Foundry Bootstrap API"


@patch("src.api.routers.status.ModelManager")
@patch("src.api.routers.status.AgentManager")
@patch("src.api.routers.status.WorkflowManager")
@patch("src.api.routers.status.DaemonService")
@patch("src.api.routers.status.TemplateLoader")
def test_status_endpoint(
    mock_template_loader,
    mock_daemon_service,
    mock_workflow_manager,
    mock_agent_manager,
    mock_model_manager,
):
    """Test the status endpoint returns correct structure."""
    # Configure mocks
    mock_model_manager.return_value.list_available_models.return_value = [MagicMock()] * 3
    mock_agent_manager.return_value.list_agents.return_value = [{}] * 5
    mock_workflow_manager.return_value.list_workflows.return_value = [{}] * 2
    mock_daemon_service.return_value.is_running.return_value = False
    mock_template_loader.return_value.list_templates.return_value = ["retail", "financial"]

    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()

    assert "status" in data
    assert "models_count" in data
    assert "agents_count" in data
    assert "workflows_count" in data
    assert "daemon_running" in data
    assert "templates_count" in data

    assert data["status"] == "ok"
    assert data["models_count"] == 3
    assert data["agents_count"] == 5
    assert data["workflows_count"] == 2
    assert data["daemon_running"] is False
    assert data["templates_count"] == 2


@patch("src.api.routers.status.ModelManager")
@patch("src.api.routers.status.AgentManager")
@patch("src.api.routers.status.WorkflowManager")
@patch("src.api.routers.status.DaemonService")
@patch("src.api.routers.status.TemplateLoader")
def test_status_handles_errors(
    mock_template_loader,
    mock_daemon_service,
    mock_workflow_manager,
    mock_agent_manager,
    mock_model_manager,
):
    """Test that status endpoint handles errors gracefully."""
    # Configure mocks to raise exceptions
    mock_model_manager.return_value.list_available_models.side_effect = Exception("Connection error")
    mock_agent_manager.return_value.list_agents.side_effect = Exception("Connection error")
    mock_workflow_manager.return_value.list_workflows.side_effect = Exception("Connection error")
    mock_daemon_service.return_value.is_running.side_effect = Exception("Connection error")
    mock_template_loader.return_value.list_templates.side_effect = Exception("Connection error")

    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()

    # Should return zeros when errors occur
    assert data["models_count"] == 0
    assert data["agents_count"] == 0
    assert data["workflows_count"] == 0
    assert data["daemon_running"] is False
    assert data["templates_count"] == 0
