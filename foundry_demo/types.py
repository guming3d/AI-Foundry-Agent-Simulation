from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AgentArchetype:
    agent_type: str
    display_name: str
    owner: str
    purpose: str
    tools: str
    query_templates: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class IndustryTemplate:
    template_id: str
    display_name: str
    default_org_id: str
    archetypes: list[AgentArchetype]
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GeneratedAgent:
    agent_id: str
    org_id: str
    agent_type: str
    name: str
    owner: str
    purpose: str
    tools: str
    model: str

