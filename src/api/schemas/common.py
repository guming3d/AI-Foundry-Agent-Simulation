"""
Common Pydantic schemas for API responses.
"""

from typing import Any, Optional
from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Standard error response."""
    success: bool = False
    error: str
    detail: Optional[str] = None


class SuccessResponse(BaseModel):
    """Standard success response."""
    success: bool = True
    message: str


class StatusResponse(BaseModel):
    """System status response."""
    status: str = "ok"
    models_count: int = 0
    agents_count: int = 0
    workflows_count: int = 0
    daemon_running: bool = False
    templates_count: int = 0
