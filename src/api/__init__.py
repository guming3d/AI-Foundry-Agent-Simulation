"""
FastAPI backend for Microsoft Foundry Bootstrap.

Provides REST API and WebSocket endpoints for the web frontend.
"""

from .main import app

__all__ = ["app"]
