"""Tests for the templates router."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from src.api.main import app


client = TestClient(app)


@patch("src.api.routers.templates.TemplateLoader")
def test_list_templates(mock_loader_class):
    """Test listing templates."""
    mock_loader = MagicMock()
    mock_loader_class.return_value = mock_loader
    mock_loader.list_templates.return_value = ["retail", "financial"]

    # Mock load_template to return profile-like objects
    def mock_load(tid):
        profile = MagicMock()
        profile.metadata.id = tid
        profile.metadata.name = f"{tid.title()} Profile"
        profile.metadata.description = f"Description for {tid}"
        profile.metadata.version = "1.0.0"
        profile.agent_types = [MagicMock()] * 3
        profile.organization.departments = [MagicMock()] * 2
        return profile

    mock_loader.load_template.side_effect = mock_load

    response = client.get("/api/templates")
    assert response.status_code == 200
    data = response.json()

    assert "templates" in data
    assert "count" in data
    assert data["count"] == 2
    assert len(data["templates"]) == 2


@patch("src.api.routers.templates.TemplateLoader")
def test_get_template_detail(mock_loader_class):
    """Test getting template details."""
    mock_loader = MagicMock()
    mock_loader_class.return_value = mock_loader

    profile = MagicMock()
    profile.metadata.id = "retail"
    profile.metadata.name = "Retail Profile"
    profile.metadata.description = "Retail industry template"
    profile.metadata.version = "1.0.0"
    profile.organization.prefix = "RETAIL"

    agent_type = MagicMock()
    agent_type.id = "customer_support"
    agent_type.name = "Customer Support"
    agent_type.department = "support"
    agent_type.description = "Handles customer queries"
    profile.agent_types = [agent_type]

    dept = MagicMock()
    dept.name = "Support"
    dept.code = "SUP"
    profile.organization.departments = [dept]

    profile.models.preferred = ["gpt-4"]
    profile.models.allowed = ["gpt-4", "gpt-35-turbo"]

    mock_loader.load_template.return_value = profile

    response = client.get("/api/templates/retail")
    assert response.status_code == 200
    data = response.json()

    assert data["id"] == "retail"
    assert data["name"] == "Retail Profile"
    assert len(data["agent_types"]) == 1
    assert data["agent_types"][0]["id"] == "customer_support"
    assert len(data["departments"]) == 1


@patch("src.api.routers.templates.TemplateLoader")
def test_get_template_not_found(mock_loader_class):
    """Test getting non-existent template."""
    from src.templates.template_loader import TemplateLoadError

    mock_loader = MagicMock()
    mock_loader_class.return_value = mock_loader
    mock_loader.load_template.side_effect = TemplateLoadError("Template not found: nonexistent")

    response = client.get("/api/templates/nonexistent")
    assert response.status_code == 404
