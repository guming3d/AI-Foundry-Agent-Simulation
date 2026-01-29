"""Tests for the WebSocket module."""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock

from src.api.websocket import ConnectionManager


@pytest.fixture
def manager():
    """Create a fresh ConnectionManager for each test."""
    return ConnectionManager()


@pytest.mark.asyncio
async def test_connect(manager):
    """Test WebSocket connection."""
    mock_websocket = AsyncMock()

    await manager.connect(mock_websocket, "simulation")

    mock_websocket.accept.assert_called_once()
    assert mock_websocket in manager.active_connections["simulation"]


@pytest.mark.asyncio
async def test_disconnect(manager):
    """Test WebSocket disconnection."""
    mock_websocket = AsyncMock()

    await manager.connect(mock_websocket, "simulation")
    assert mock_websocket in manager.active_connections["simulation"]

    await manager.disconnect(mock_websocket, "simulation")
    assert mock_websocket not in manager.active_connections["simulation"]


@pytest.mark.asyncio
async def test_broadcast(manager):
    """Test broadcasting to all connections."""
    mock_ws1 = AsyncMock()
    mock_ws2 = AsyncMock()

    await manager.connect(mock_ws1, "simulation")
    await manager.connect(mock_ws2, "simulation")

    message = {"type": "test", "data": "hello"}
    await manager.broadcast(message, "simulation")

    mock_ws1.send_json.assert_called_once_with(message)
    mock_ws2.send_json.assert_called_once_with(message)


@pytest.mark.asyncio
async def test_broadcast_removes_disconnected(manager):
    """Test that broadcast removes disconnected clients."""
    mock_ws1 = AsyncMock()
    mock_ws2 = AsyncMock()
    mock_ws2.send_json.side_effect = Exception("Connection closed")

    await manager.connect(mock_ws1, "simulation")
    await manager.connect(mock_ws2, "simulation")

    message = {"type": "test"}
    await manager.broadcast(message, "simulation")

    # ws2 should be removed after failed send
    assert mock_ws1 in manager.active_connections["simulation"]
    assert mock_ws2 not in manager.active_connections["simulation"]


@pytest.mark.asyncio
async def test_send_personal(manager):
    """Test sending to a specific connection."""
    mock_websocket = AsyncMock()

    message = {"type": "personal", "data": "for you only"}
    await manager.send_personal(mock_websocket, message)

    mock_websocket.send_json.assert_called_once_with(message)


@pytest.mark.asyncio
async def test_send_personal_handles_error(manager):
    """Test that send_personal handles errors gracefully."""
    mock_websocket = AsyncMock()
    mock_websocket.send_json.side_effect = Exception("Connection closed")

    # Should not raise
    await manager.send_personal(mock_websocket, {"test": "data"})


def test_get_connection_count(manager):
    """Test getting connection count."""
    # Initially empty
    assert manager.get_connection_count() == 0
    assert manager.get_connection_count("simulation") == 0

    # Add some mock connections manually
    mock_ws = MagicMock()
    manager.active_connections["simulation"].add(mock_ws)

    assert manager.get_connection_count("simulation") == 1
    assert manager.get_connection_count() == 1


def test_multiple_channels(manager):
    """Test connections to multiple channels."""
    mock_ws1 = MagicMock()
    mock_ws2 = MagicMock()

    manager.active_connections["simulation"].add(mock_ws1)
    manager.active_connections["daemon"].add(mock_ws2)

    assert manager.get_connection_count("simulation") == 1
    assert manager.get_connection_count("daemon") == 1
    assert manager.get_connection_count() == 2
