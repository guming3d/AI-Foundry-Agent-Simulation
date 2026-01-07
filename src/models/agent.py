"""
Agent data models for Azure AI Foundry Agent Toolkit.

These models define the structure for agent creation, configuration,
and management within the toolkit.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class AgentConfig(BaseModel):
    """Configuration for an agent type within an industry profile."""

    id: str = Field(..., description="Agent type identifier (e.g., 'CustomerSupport')")
    name: str = Field(..., description="Human-readable agent name")
    department: str = Field(..., description="Department code this agent belongs to")
    description: Optional[str] = Field(None, description="Agent purpose description")
    instructions: str = Field(..., description="System instructions for the agent")
    tools: List[str] = Field(default_factory=list, description="Available tools for this agent")
    query_templates: List[str] = Field(default_factory=list, description="Query templates for simulation")


class AgentCreateRequest(BaseModel):
    """Request model for creating a new agent."""

    org_id: str = Field(..., description="Organization ID (e.g., 'ORG01', 'RETAIL01')")
    agent_type: str = Field(..., description="Agent type identifier")
    agent_id: str = Field(..., description="Unique agent ID within org (e.g., 'AG001')")
    model: str = Field(..., description="Model to use for this agent")
    instructions: str = Field(..., description="System instructions for the agent")

    @property
    def agent_name(self) -> str:
        """Generate the full agent name in format: {org_id}-{agent_type}-{agent_id}"""
        return f"{self.org_id}-{self.agent_type.replace(' ', '')}-{self.agent_id}"


class Agent(BaseModel):
    """Represents an agent definition (before creation in Azure)."""

    agent_id: str = Field(..., description="Local agent ID")
    org_id: str = Field(..., description="Organization ID")
    agent_type: str = Field(..., description="Agent type identifier")
    name: str = Field(..., description="Full agent name")
    model: str = Field(..., description="Model assigned to this agent")
    instructions: str = Field(..., description="System instructions")
    tools: List[str] = Field(default_factory=list, description="Available tools")
    department: Optional[str] = Field(None, description="Department code")

    @classmethod
    def from_create_request(cls, request: AgentCreateRequest, tools: List[str] = None, department: str = None) -> "Agent":
        """Create an Agent from a create request."""
        return cls(
            agent_id=request.agent_id,
            org_id=request.org_id,
            agent_type=request.agent_type,
            name=request.agent_name,
            model=request.model,
            instructions=request.instructions,
            tools=tools or [],
            department=department,
        )


class CreatedAgent(BaseModel):
    """Represents an agent that has been created in Azure AI Foundry."""

    agent_id: str = Field(..., description="Local agent ID")
    name: str = Field(..., description="Full agent name")
    azure_id: str = Field(..., description="Azure-assigned agent ID")
    version: int = Field(..., description="Agent version number")
    model: str = Field(..., description="Model used by this agent")
    org_id: str = Field(..., description="Organization ID")
    agent_type: Optional[str] = Field(None, description="Agent type identifier")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")

    def to_csv_dict(self) -> dict:
        """Convert to dictionary for CSV export (matches existing format)."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "azure_id": self.azure_id,
            "version": self.version,
            "model": self.model,
            "org_id": self.org_id,
        }

    @classmethod
    def from_csv_row(cls, row: dict) -> "CreatedAgent":
        """Create from a CSV row dictionary."""
        # Extract agent_type from name if present (format: ORG-AgentType-ID)
        agent_type = None
        name_parts = row.get("name", "").split("-")
        if len(name_parts) >= 2:
            agent_type = name_parts[1]

        return cls(
            agent_id=row["agent_id"],
            name=row["name"],
            azure_id=row["azure_id"],
            version=int(row["version"]),
            model=row["model"],
            org_id=row["org_id"],
            agent_type=agent_type,
        )


class AgentBatchResult(BaseModel):
    """Result of a batch agent creation operation."""

    created: List[CreatedAgent] = Field(default_factory=list, description="Successfully created agents")
    failed: List[dict] = Field(default_factory=list, description="Failed agent creation attempts")

    @property
    def total_attempted(self) -> int:
        return len(self.created) + len(self.failed)

    @property
    def success_rate(self) -> float:
        if self.total_attempted == 0:
            return 0.0
        return len(self.created) / self.total_attempted * 100
