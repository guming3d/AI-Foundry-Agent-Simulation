"""
Agent management for Microsoft Foundry Agent Toolkit.

Provides CRUD operations for AI agents:
- Create agents from industry profiles
- List existing agents
- Delete agents
- Batch operations
"""

import csv
import random
from typing import List, Optional, Dict, Any
from pathlib import Path
from azure.ai.projects.models import PromptAgentDefinition

from .azure_client import get_project_client
from . import config
from ..models.agent import Agent, AgentCreateRequest, CreatedAgent, AgentBatchResult
from ..models.industry_profile import IndustryProfile, AgentType


class AgentManager:
    """
    Manager for Microsoft Foundry agents.

    Handles agent creation, listing, and deletion with support for
    industry profiles and batch operations.
    """

    def __init__(self, models: List[str] = None):
        """
        Initialize the agent manager.

        Args:
            models: List of available models for random assignment.
                   If not provided, models will be fetched from Microsoft Foundry.
        """
        self.models = models or []

    def create_agent_name(self, org_id: str, agent_type: str, agent_id: str) -> str:
        """
        Create a standardized agent name.

        Args:
            org_id: Organization ID (e.g., 'ORG01', 'RETAIL01')
            agent_type: Agent type identifier (e.g., 'CustomerSupport')
            agent_id: Unique agent ID (e.g., 'AG001')

        Returns:
            Formatted agent name: {org_id}-{agent_type}-{agent_id}
        """
        clean_type = agent_type.replace(' ', '').replace('Agent', '')
        return f"{org_id}-{clean_type}-{agent_id}"

    def create_agent_instructions(
        self,
        purpose: str,
        tools: List[str] = None,
        department: str = None,
        custom_instructions: str = None
    ) -> str:
        """
        Create detailed instructions for an agent.

        Args:
            purpose: Agent's purpose description
            tools: List of available tools
            department: Department name
            custom_instructions: Optional custom instruction template

        Returns:
            Formatted instruction string
        """
        if custom_instructions:
            return custom_instructions

        tools_str = ", ".join(tools) if tools else "General assistance"
        dept_str = department or "General"

        return f"""You are a specialized AI agent for {purpose}.

Your capabilities include:
- Tools: {tools_str}
- Department: {dept_str}

Please assist users with tasks related to your area of expertise while maintaining professional standards and following all applicable policies."""

    def create_agent(self, request: AgentCreateRequest) -> CreatedAgent:
        """
        Create a single agent in Microsoft Foundry.

        Args:
            request: Agent creation request

        Returns:
            CreatedAgent with Azure details

        Raises:
            Exception: If agent creation fails
        """
        client = get_project_client()

        agent = client.agents.create_version(
            agent_name=request.agent_name,
            definition=PromptAgentDefinition(
                model=request.model,
                instructions=request.instructions,
            ),
        )

        return CreatedAgent(
            agent_id=request.agent_id,
            name=request.agent_name,
            azure_id=agent.id,
            version=agent.version,
            model=request.model,
            org_id=request.org_id,
            agent_type=request.agent_type,
        )

    def create_agents_from_profile(
        self,
        profile: IndustryProfile,
        agent_count: int,
        org_count: int = 1,
        models: List[str] = None,
        progress_callback=None
    ) -> AgentBatchResult:
        """
        Create agents based on an industry profile.

        Args:
            profile: Industry profile defining agent types
            agent_count: Number of agents to create per type per org
            org_count: Number of organizations to create
            models: List of models to randomly assign (required - must be provided)
            progress_callback: Optional callback(current, total, message) for progress updates

        Returns:
            AgentBatchResult with created and failed agents
        """
        result = AgentBatchResult()
        available_models = models or self.models

        if not available_models:
            raise ValueError(
                "No models provided. Please select models from your Microsoft Foundry project."
            )

        # Calculate total agents
        total_agents = len(profile.agent_types) * agent_count * org_count
        current = 0

        for org_num in range(1, org_count + 1):
            # Use 3-digit org IDs to support up to 999 organizations
            org_id = f"{profile.organization.prefix}{org_num:03d}"

            for agent_type in profile.agent_types:
                for agent_num in range(1, agent_count + 1):
                    current += 1
                    agent_id = f"AG{agent_num:03d}"

                    # Random model selection
                    selected_model = random.choice(available_models)

                    # Create agent name
                    agent_name = self.create_agent_name(org_id, agent_type.id, agent_id)

                    # Create instructions
                    instructions = self.create_agent_instructions(
                        purpose=agent_type.description or agent_type.name,
                        tools=agent_type.tools,
                        department=agent_type.department,
                        custom_instructions=agent_type.instructions,
                    )

                    if progress_callback:
                        progress_callback(current, total_agents, f"Creating {agent_name}...")

                    try:
                        request = AgentCreateRequest(
                            org_id=org_id,
                            agent_type=agent_type.id,
                            agent_id=agent_id,
                            model=selected_model,
                            instructions=instructions,
                        )

                        created = self.create_agent(request)
                        result.created.append(created)

                    except Exception as e:
                        result.failed.append({
                            "agent_id": agent_id,
                            "name": agent_name,
                            "org_id": org_id,
                            "agent_type": agent_type.id,
                            "error": str(e),
                        })

        return result

    def list_agents(self) -> List[Dict[str, Any]]:
        """
        List all agents in the project.

        Returns:
            List of agent dictionaries with name, id, version, and model info
        """
        client = get_project_client()
        agents = []

        try:
            for agent in client.agents.list():
                # Extract version and model from nested structure
                version = None
                model = None

                # Agent object has 'versions' attribute with 'latest' version info
                if hasattr(agent, 'versions'):
                    try:
                        # Access latest version (works like a dict but is AgentObjectVersions)
                        latest = agent.versions.get('latest', {})
                        if latest:
                            version = latest.get('version')

                            # Model is in definition.model
                            definition = latest.get('definition', {})
                            if definition:
                                model = definition.get('model')
                    except Exception as e:
                        print(f"Error extracting version/model for agent {agent.name}: {e}")

                agents.append({
                    "name": agent.name,
                    "id": agent.id,
                    "version": version,
                    "model": model,
                })
        except Exception as e:
            print(f"Error listing agents: {e}")

        return agents

    def get_agent(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """
        Get details for a specific agent.

        Args:
            agent_name: Name of the agent

        Returns:
            Agent details dictionary or None if not found
        """
        client = get_project_client()

        try:
            agent = client.agents.get(agent_name=agent_name)
            return {
                "name": agent.name,
                "id": agent.id,
                "version": getattr(agent, 'version', None),
                "model": getattr(agent, 'model', None),
            }
        except Exception as e:
            print(f"Error getting agent {agent_name}: {e}")
            return None

    def delete_agent(self, agent_name: str) -> bool:
        """
        Delete an agent.

        Args:
            agent_name: Name of the agent to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        client = get_project_client()

        try:
            client.agents.delete(agent_name=agent_name)
            return True
        except Exception as e:
            print(f"Error deleting agent {agent_name}: {e}")
            return False

    def delete_all_agents(self, progress_callback=None) -> Dict[str, Any]:
        """
        Delete all agents in the project.

        Args:
            progress_callback: Optional callback(current, total, message) for progress updates

        Returns:
            Dictionary with deleted, failed lists and total count
        """
        agents = self.list_agents()
        deleted = []
        failed = []
        total = len(agents)

        if progress_callback:
            progress_callback(0, total, f"Found {total} agents to delete...")

        for i, agent in enumerate(agents):
            agent_name = agent.get('name', '')
            if progress_callback:
                progress_callback(i + 1, total, f"Deleting {agent_name}...")

            if self.delete_agent(agent_name):
                deleted.append(agent)
            else:
                failed.append(agent)

        return {
            "deleted": deleted,
            "failed": failed,
            "total": total,
            "deleted_count": len(deleted),
            "failed_count": len(failed),
        }

    def save_agents_to_csv(
        self,
        agents: List[CreatedAgent],
        output_path: str = None
    ) -> None:
        """
        Save created agents to a CSV file.

        Args:
            agents: List of created agents
            output_path: Output CSV file path (defaults to results/agents/created_agents_results.csv)
        """
        if not agents:
            return

        # Use default path if not specified
        if output_path is None:
            config.ensure_directories()
            output_path = str(config.CREATED_AGENTS_CSV)

        # Ensure parent directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        fieldnames = ["agent_id", "name", "azure_id", "version", "model", "org_id"]

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for agent in agents:
                writer.writerow(agent.to_csv_dict())

    def load_agents_from_csv(self, csv_path: str) -> List[CreatedAgent]:
        """
        Load agents from a CSV file.

        Args:
            csv_path: Path to the CSV file

        Returns:
            List of CreatedAgent objects
        """
        agents = []
        path = Path(csv_path)

        if not path.exists():
            return agents

        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                agents.append(CreatedAgent.from_csv_row(row))

        return agents

    def save_failed_to_csv(
        self,
        failed: List[Dict],
        output_path: str = None
    ) -> None:
        """
        Save failed agent creation attempts to a CSV file.

        Args:
            failed: List of failed attempt dictionaries
            output_path: Output CSV file path (defaults to results/agents/failed_agents_results.csv)
        """
        if not failed:
            return

        # Use default path if not specified
        if output_path is None:
            config.ensure_directories()
            output_path = str(config.FAILED_AGENTS_CSV)

        # Ensure parent directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        fieldnames = ["agent_id", "name", "org_id", "agent_type", "error"]

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(failed)


# Convenience function for quick agent creation
def create_agents_quick(
    profile: IndustryProfile,
    agent_count: int = 1,
    org_count: int = 1,
    models: List[str] = None,
    output_csv: str = None
) -> AgentBatchResult:
    """
    Quick function to create agents from a profile and save to CSV.

    Args:
        profile: Industry profile
        agent_count: Agents per type per org
        org_count: Number of organizations
        models: Models to use (random selection)
        output_csv: Output CSV path (defaults to results/agents/created_agents_results.csv)

    Returns:
        AgentBatchResult
    """
    manager = AgentManager(models=models)
    result = manager.create_agents_from_profile(
        profile=profile,
        agent_count=agent_count,
        org_count=org_count,
    )

    if result.created:
        manager.save_agents_to_csv(result.created, output_csv)

    if result.failed:
        manager.save_failed_to_csv(result.failed)

    return result
