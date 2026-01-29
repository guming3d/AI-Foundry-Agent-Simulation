"""
WebSocket connection manager for real-time updates.
"""

import asyncio
import json
from typing import Dict, List, Set, Any
from fastapi import WebSocket, WebSocketDisconnect


class ConnectionManager:
    """
    Manages WebSocket connections for real-time updates.

    Supports multiple channels for different types of updates:
    - simulation: Real-time simulation progress
    - daemon: Daemon metrics updates
    """

    def __init__(self):
        # Channel -> set of connections
        self.active_connections: Dict[str, Set[WebSocket]] = {
            "simulation": set(),
            "daemon": set(),
        }
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, channel: str = "simulation"):
        """Accept a WebSocket connection and add to channel."""
        await websocket.accept()
        async with self._lock:
            if channel not in self.active_connections:
                self.active_connections[channel] = set()
            self.active_connections[channel].add(websocket)

    async def disconnect(self, websocket: WebSocket, channel: str = "simulation"):
        """Remove a WebSocket connection from channel."""
        async with self._lock:
            if channel in self.active_connections:
                self.active_connections[channel].discard(websocket)

    async def broadcast(self, message: Dict[str, Any], channel: str = "simulation"):
        """Broadcast a message to all connections in a channel."""
        async with self._lock:
            connections = list(self.active_connections.get(channel, set()))

        disconnected = []
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)

        # Clean up disconnected clients
        if disconnected:
            async with self._lock:
                for conn in disconnected:
                    self.active_connections.get(channel, set()).discard(conn)

    async def send_personal(self, websocket: WebSocket, message: Dict[str, Any]):
        """Send a message to a specific connection."""
        try:
            await websocket.send_json(message)
        except Exception:
            pass

    def get_connection_count(self, channel: str = None) -> int:
        """Get the number of active connections."""
        if channel:
            return len(self.active_connections.get(channel, set()))
        return sum(len(conns) for conns in self.active_connections.values())


# Global connection manager instance
manager = ConnectionManager()


async def simulation_websocket_handler(websocket: WebSocket):
    """Handle WebSocket connections for simulation updates."""
    await manager.connect(websocket, "simulation")
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            # Echo back or handle commands if needed
            await manager.send_personal(websocket, {"type": "ack", "data": data})
    except WebSocketDisconnect:
        await manager.disconnect(websocket, "simulation")


async def daemon_websocket_handler(websocket: WebSocket):
    """Handle WebSocket connections for daemon updates."""
    await manager.connect(websocket, "daemon")
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            await manager.send_personal(websocket, {"type": "ack", "data": data})
    except WebSocketDisconnect:
        await manager.disconnect(websocket, "daemon")


# Helper functions for broadcasting updates
async def broadcast_simulation_update(data: Dict[str, Any]):
    """Broadcast a simulation update to all connected clients."""
    await manager.broadcast({"type": "simulation_update", "data": data}, "simulation")


async def broadcast_daemon_update(data: Dict[str, Any]):
    """Broadcast a daemon update to all connected clients."""
    await manager.broadcast({"type": "daemon_update", "data": data}, "daemon")
