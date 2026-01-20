"""
Workflow models for Microsoft Foundry Agent Toolkit.

Defines workflow templates, roles, and created workflow records.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

from .industry_profile import AgentType


class WorkflowRole(BaseModel):
    """Role definition within a workflow template."""

    id: str = Field(..., description="Role identifier (e.g., 'intake', 'reviewer')")
    name: str = Field(..., description="Human-readable role name")
    agent_type: AgentType = Field(..., description="Agent type used for this role")
    instructions_suffix: Optional[str] = Field(
        None,
        description="Extra instructions appended to the agent prompt for this role",
    )


class WorkflowTemplate(BaseModel):
    """Workflow template composed of roles and a workflow pattern."""

    id: str = Field(..., description="Template identifier")
    name: str = Field(..., description="Template display name")
    description: str = Field(..., description="Template description")
    pattern: str = Field(..., description="Workflow pattern (sequential or review_loop)")
    roles: List[WorkflowRole] = Field(default_factory=list, description="Ordered workflow roles")


class CreatedWorkflow(BaseModel):
    """Represents a workflow created in Microsoft Foundry."""

    name: str = Field(..., description="Workflow agent name")
    azure_id: str = Field(..., description="Azure workflow agent ID")
    version: int = Field(..., description="Workflow agent version")
    org_id: str = Field(..., description="Organization ID")
    template_id: str = Field(..., description="Template identifier")
    template_name: str = Field(..., description="Template display name")
    agent_names: List[str] = Field(default_factory=list, description="Agent names used in the workflow")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")


class WorkflowBatchResult(BaseModel):
    """Result of a batch workflow creation operation."""

    created: List[CreatedWorkflow] = Field(default_factory=list, description="Successfully created workflows")
    failed: List[dict] = Field(default_factory=list, description="Failed workflow creation attempts")

    @property
    def total_attempted(self) -> int:
        return len(self.created) + len(self.failed)
