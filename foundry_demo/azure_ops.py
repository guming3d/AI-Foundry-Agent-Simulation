from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Optional

from .errors import MissingDependencyError
from .instructions import build_agent_instructions
from .types import GeneratedAgent


def _require_azure() -> tuple[Any, Any, Any]:
    try:
        from azure.identity import DefaultAzureCredential  # type: ignore
        from azure.ai.projects import AIProjectClient  # type: ignore
        from azure.ai.projects.models import PromptAgentDefinition  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise MissingDependencyError(
            "Azure SDK dependencies missing. Install with:\n"
            "  `pip install azure-identity openai azure-ai-projects==2.0.0b3`\n"
            "Then authenticate with `az login` (or service principal env vars)."
        ) from exc
    return DefaultAzureCredential, AIProjectClient, PromptAgentDefinition


@dataclass(frozen=True)
class DeploymentInfo:
    name: str
    model_publisher: Optional[str]
    model_name: Optional[str]
    deployment_type: Optional[str]


class FoundryProject:
    def __init__(self, *, endpoint: str):
        DefaultAzureCredential, AIProjectClient, _ = _require_azure()
        self._client = AIProjectClient(endpoint=endpoint, credential=DefaultAzureCredential())
        self._openai = self._client.get_openai_client()

    def list_deployments(self) -> list[DeploymentInfo]:
        deployments = []
        for item in self._client.deployments.list():
            # Deployment is a MutableMapping; keys vary by api-version
            name = str(item.get("name") or item.get("deploymentName") or "")
            deployments.append(
                DeploymentInfo(
                    name=name,
                    model_publisher=item.get("modelPublisher"),
                    model_name=item.get("modelName"),
                    deployment_type=str(item.get("deploymentType")) if item.get("deploymentType") is not None else None,
                )
            )
        return deployments

    def create_agents(
        self, *, agents: Iterable[GeneratedAgent]
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        _, _, PromptAgentDefinition = _require_azure()
        created_results: list[dict[str, Any]] = []
        failed_results: list[dict[str, Any]] = []
        for agent in agents:
            agent_name = agent.name
            model = agent.model
            instructions = build_agent_instructions(agent)
            try:
                created = self._client.agents.create_version(
                    agent_name=agent_name,
                    definition=PromptAgentDefinition(model=model, instructions=instructions),
                )
                created_results.append(
                    {
                        "agent_id": agent.agent_id,
                        "name": created.name,
                        "azure_id": created.id,
                        "version": created.version,
                        "model": model,
                        "org_id": agent.org_id,
                    }
                )
            except Exception as exc:  # pragma: no cover  # noqa: BLE001
                failed_results.append(
                    {
                        "agent_id": agent.agent_id,
                        "name": agent.name,
                        "model": agent.model,
                        "org_id": agent.org_id,
                        "error": str(exc),
                    }
                )
        return created_results, failed_results

    def call_agent(self, *, agent_name: str, user_input: str) -> str:
        response = self._openai.responses.create(
            input=user_input,
            extra_body={"agent": {"name": agent_name, "type": "agent_reference"}},
        )
        return getattr(response, "output_text", "")
