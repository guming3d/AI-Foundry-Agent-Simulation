"""
Pydantic schemas for agent-related API endpoints.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class AgentResponse(BaseModel):
    """Single agent response."""
    name: str
    id: str
    version: Optional[int] = None
    model: Optional[str] = None


class AgentListResponse(BaseModel):
    """List of agents response."""
    agents: List[AgentResponse]
    count: int


class CreateAgentsRequest(BaseModel):
    """Request to create agents from a profile."""
    profile_id: str = Field(..., description="Industry profile ID")
    agent_count: int = Field(default=1, ge=1, le=100, description="Agents per type per org")
    org_count: int = Field(default=1, ge=1, le=100, description="Number of organizations")
    models: List[str] = Field(..., min_length=1, description="Models to use for agents")


class CreatedAgentInfo(BaseModel):
    """Info about a successfully created agent."""
    agent_id: str
    name: str
    azure_id: str
    version: int
    model: str
    org_id: str


class FailedAgentInfo(BaseModel):
    """Info about a failed agent creation."""
    agent_id: str
    name: str
    org_id: str
    agent_type: str
    error: str


class CreateAgentsResponse(BaseModel):
    """Response from agent creation."""
    success: bool
    created: List[CreatedAgentInfo] = []
    failed: List[FailedAgentInfo] = []
    total_attempted: int
    created_count: int
    failed_count: int


class DeleteAgentsResponse(BaseModel):
    """Response from agent deletion."""
    success: bool
    deleted_count: int
    failed_count: int
    total: int
    message: str
