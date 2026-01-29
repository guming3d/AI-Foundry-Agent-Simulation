"""Tests for the daemon router."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from src.api.main import app


client = TestClient(app)


@patch("src.api.routers.daemon.DaemonService")
def test_get_daemon_status_stopped(mock_service_class):
    """Test getting daemon status when stopped."""
    mock_service = MagicMock()
    mock_service_class.return_value = mock_service
    mock_service.is_running.return_value = False
    mock_service.read_state.return_value = {}
    mock_service.read_metrics.return_value = {}

    response = client.get("/api/daemon/status")
    assert response.status_code == 200
    data = response.json()

    assert data["is_running"] is False
    assert data["metrics"] is None


@patch("src.api.routers.daemon.DaemonService")
def test_get_daemon_status_running(mock_service_class):
    """Test getting daemon status when running."""
    mock_service = MagicMock()
    mock_service_class.return_value = mock_service
    mock_service.is_running.return_value = True
    mock_service.read_state.return_value = {
        "started_at": "2024-01-15T10:00:00",
        "profile_id": "retail",
        "profile_name": "Retail Profile",
    }
    mock_service.read_metrics.return_value = {
        "total_calls": 100,
        "successful_calls": 95,
        "failed_calls": 5,
        "success_rate": 95.0,
        "avg_latency_ms": 250,
        "runtime": "5m 30s",
    }

    response = client.get("/api/daemon/status")
    assert response.status_code == 200
    data = response.json()

    assert data["is_running"] is True
    assert data["profile_id"] == "retail"
    assert data["metrics"]["total_calls"] == 100


@patch("src.api.routers.daemon.DaemonService")
def test_stop_daemon_not_running(mock_service_class):
    """Test stopping daemon when not running."""
    mock_service = MagicMock()
    mock_service_class.return_value = mock_service
    mock_service.is_running.return_value = False

    response = client.post("/api/daemon/stop")
    assert response.status_code == 200
    data = response.json()

    assert data["success"] is False
    assert "not running" in data["message"].lower()


@patch("src.api.routers.daemon.DaemonService")
def test_stop_daemon_running(mock_service_class):
    """Test stopping daemon when running."""
    mock_service = MagicMock()
    mock_service_class.return_value = mock_service
    mock_service.is_running.return_value = True
    mock_service.stop.return_value = (True, "Daemon stopped")

    response = client.post("/api/daemon/stop")
    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    mock_service.stop.assert_called_once()


@patch("src.api.routers.daemon.DaemonService")
def test_get_daemon_metrics(mock_service_class):
    """Test getting daemon metrics."""
    mock_service = MagicMock()
    mock_service_class.return_value = mock_service
    mock_service.read_metrics.return_value = {
        "total_calls": 500,
        "scheduled_calls": 520,
        "started_calls": 510,
        "dropped_calls": 10,
        "successful_calls": 480,
        "failed_calls": 20,
        "success_rate": 96.0,
        "avg_latency_ms": 200,
        "p50_latency_ms": 180,
        "p95_latency_ms": 450,
        "max_latency_ms": 1200,
        "calls_per_minute": 10,
        "runtime": "50m 0s",
    }

    response = client.get("/api/daemon/metrics")
    assert response.status_code == 200
    data = response.json()

    assert data["total_calls"] == 500
    assert data["success_rate"] == 96.0


@patch("src.api.routers.daemon.DaemonService")
def test_get_daemon_history(mock_service_class):
    """Test getting daemon history."""
    mock_service = MagicMock()
    mock_service_class.return_value = mock_service
    mock_service.read_history.return_value = [
        {"timestamp": "2024-01-15T10:00:00", "total_calls": 10, "total_operations": 8, "total_guardrails": 2},
        {"timestamp": "2024-01-15T10:01:00", "total_calls": 25, "total_operations": 20, "total_guardrails": 5},
    ]

    response = client.get("/api/daemon/history?limit=60")
    assert response.status_code == 200
    data = response.json()

    assert "history" in data
    assert len(data["history"]) == 2
    mock_service.read_history.assert_called_once_with(limit=60)
