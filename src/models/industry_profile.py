"""
Industry profile data models for Microsoft Foundry Agent Toolkit.

These models define the structure for industry-specific templates
that configure agent types, query templates, and guardrail tests.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class DepartmentConfig(BaseModel):
    """Configuration for a department within an organization."""

    name: str = Field(..., description="Department name (e.g., 'Customer Experience')")
    code: str = Field(..., description="Department code (e.g., 'CX')")


class OrganizationConfig(BaseModel):
    """Organization structure configuration."""

    prefix: str = Field(..., description="Organization ID prefix (e.g., 'RETAIL')")
    departments: List[DepartmentConfig] = Field(default_factory=list, description="List of departments")


class ModelConfig(BaseModel):
    """Model configuration for an industry profile."""

    preferred: List[str] = Field(default_factory=list, description="Preferred models for this industry")
    allowed: List[str] = Field(default_factory=list, description="All allowed models")


class QueryTemplate(BaseModel):
    """A query template with placeholder support."""

    template: str = Field(..., description="Query template string with {} placeholders")
    description: Optional[str] = Field(None, description="Description of what this query tests")

    def render(self, *args) -> str:
        """Render the template with provided arguments."""
        return self.template.format(*args)


class AgentType(BaseModel):
    """Definition of an agent type within an industry profile."""

    id: str = Field(..., description="Agent type identifier (e.g., 'CustomerSupport')")
    name: str = Field(..., description="Human-readable agent name")
    department: str = Field(..., description="Department code this agent belongs to")
    description: Optional[str] = Field(None, description="Agent purpose description")
    instructions: str = Field(..., description="System instructions template for the agent")
    tools: List[str] = Field(default_factory=list, description="Available tools for this agent")
    query_templates: List[str] = Field(default_factory=list, description="Query templates for simulation")


class GuardrailTests(BaseModel):
    """Guardrail test queries organized by category."""

    harms_content: List[str] = Field(default_factory=list, description="Harmful content test queries")
    jailbreak_content: List[str] = Field(default_factory=list, description="Jailbreak attempt queries")
    indirect_prompt_injection: List[str] = Field(default_factory=list, description="Prompt injection tests")
    self_harm_content: List[str] = Field(default_factory=list, description="Self-harm content queries")
    sexual_content: List[str] = Field(default_factory=list, description="Sexual content test queries")
    pii_exposure: List[str] = Field(default_factory=list, description="PII exposure test queries")
    data_exfiltration: List[str] = Field(default_factory=list, description="Data exfiltration attempts")

    def get_all_tests(self) -> Dict[str, List[str]]:
        """Get all test categories as a dictionary."""
        return {
            "harms_content": self.harms_content,
            "jailbreak_content": self.jailbreak_content,
            "indirect_prompt_injection": self.indirect_prompt_injection,
            "self_harm_content": self.self_harm_content,
            "sexual_content": self.sexual_content,
            "pii_exposure": self.pii_exposure,
            "data_exfiltration": self.data_exfiltration,
        }

    def get_non_empty_categories(self) -> Dict[str, List[str]]:
        """Get only categories that have test queries."""
        return {k: v for k, v in self.get_all_tests().items() if v}


class ProfileMetadata(BaseModel):
    """Metadata for an industry profile."""

    id: str = Field(..., description="Profile identifier (e.g., 'retail')")
    name: str = Field(..., description="Display name (e.g., 'Retail/E-commerce')")
    description: Optional[str] = Field(None, description="Profile description")
    version: str = Field(default="1.0.0", description="Profile version")


class DaemonProfileConfig(BaseModel):
    """Daemon configuration specific to an industry profile."""

    target_daily_requests: Dict[str, int] = Field(
        default_factory=lambda: {"min": 3000, "max": 5000},
        description="Target daily request range"
    )
    execution_interval_minutes: int = Field(default=15, description="Execution interval")
    simulation_mix: Dict[str, int] = Field(
        default_factory=lambda: {"operations_weight": 70, "guardrails_weight": 30},
        description="Simulation type mix weights"
    )
    load_profiles: Optional[Dict] = Field(None, description="Custom load profiles")


class IndustryProfile(BaseModel):
    """Complete industry profile configuration."""

    metadata: ProfileMetadata = Field(..., description="Profile metadata")
    organization: OrganizationConfig = Field(..., description="Organization structure")
    models: ModelConfig = Field(..., description="Model configuration")
    agent_types: List[AgentType] = Field(default_factory=list, description="Agent type definitions")
    guardrail_tests: GuardrailTests = Field(default_factory=GuardrailTests, description="Guardrail tests")
    daemon_config: DaemonProfileConfig = Field(
        default_factory=DaemonProfileConfig,
        description="Daemon configuration"
    )

    def get_agent_type(self, type_id: str) -> Optional[AgentType]:
        """Get an agent type by its ID."""
        for agent_type in self.agent_types:
            if agent_type.id == type_id:
                return agent_type
        return None

    def get_department(self, code: str) -> Optional[DepartmentConfig]:
        """Get a department by its code."""
        for dept in self.organization.departments:
            if dept.code == code:
                return dept
        return None

    def get_query_templates_dict(self) -> Dict[str, List[str]]:
        """Get query templates as a dictionary keyed by agent type ID."""
        return {
            agent_type.id: agent_type.query_templates
            for agent_type in self.agent_types
        }

    @property
    def agent_type_ids(self) -> List[str]:
        """Get list of all agent type IDs."""
        return [at.id for at in self.agent_types]

    @property
    def total_agent_types(self) -> int:
        """Get total number of agent types."""
        return len(self.agent_types)
