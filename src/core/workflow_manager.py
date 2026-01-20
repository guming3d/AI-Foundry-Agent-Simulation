"""
Workflow management for Microsoft Foundry Agent Toolkit.

Provides workflow template building and batch workflow creation.
"""

from __future__ import annotations

import random
import re
from typing import List, Optional, Dict, Any

from azure.ai.projects.models import PromptAgentDefinition, WorkflowAgentDefinition

from .azure_client import get_project_client
from ..models.industry_profile import IndustryProfile, AgentType
from ..models.workflow import WorkflowTemplate, WorkflowRole, CreatedWorkflow, WorkflowBatchResult


class WorkflowManager:
    """Manager for creating workflow agents and related prompt agents."""

    def __init__(self, models: Optional[List[str]] = None):
        self.models = models or []

    def list_workflows(self) -> List[Dict[str, Any]]:
        """
        List workflow agents in the project.

        Returns:
            List of workflow agent dictionaries with name, id, and version info
        """
        client = get_project_client()
        workflows = []

        try:
            for agent in client.agents.list():
                version, definition = self._get_latest_version_definition(agent)
                if not self._is_workflow_definition(definition):
                    continue

                workflows.append({
                    "name": agent.name,
                    "id": agent.id,
                    "version": version,
                })
        except Exception as e:
            print(f"Error listing workflows: {e}")

        return workflows

    @staticmethod
    def _get_latest_version_definition(agent: Any) -> tuple[Optional[int], Any]:
        """Extract the latest version and definition from an agent object."""
        version = None
        definition = None

        if hasattr(agent, "versions"):
            try:
                latest = agent.versions.get("latest", None)
            except Exception:
                latest = None

            if latest:
                if isinstance(latest, dict):
                    version = latest.get("version")
                    definition = latest.get("definition")
                else:
                    version = getattr(latest, "version", None)
                    definition = getattr(latest, "definition", None)

        return version, definition

    @staticmethod
    def _is_workflow_definition(definition: Any) -> bool:
        """Check whether a definition represents a workflow agent."""
        if not definition:
            return False

        if isinstance(definition, dict):
            if "workflow" in definition:
                return True
            definition_type = definition.get("type") or definition.get("kind")
            return isinstance(definition_type, str) and "workflow" in definition_type.lower()

        if getattr(definition, "workflow", None):
            return True

        return hasattr(definition, "workflow")

    @staticmethod
    def build_templates(profile: IndustryProfile) -> List[WorkflowTemplate]:
        """Build workflow templates from an industry profile."""
        if not profile or not profile.agent_types:
            return []

        agent_types = profile.agent_types

        def pick_agent(
            keywords: List[str],
            exclude_ids: Optional[set[str]] = None,
        ) -> Optional[AgentType]:
            exclude_ids = exclude_ids or set()
            for agent_type in agent_types:
                if agent_type.id in exclude_ids:
                    continue
                haystack = " ".join(
                    [
                        agent_type.id,
                        agent_type.name,
                        agent_type.description or "",
                    ]
                ).lower()
                if any(keyword in haystack for keyword in keywords):
                    return agent_type
            for agent_type in agent_types:
                if agent_type.id not in exclude_ids:
                    return agent_type
            return None

        intake_keywords = [
            "support",
            "service",
            "customer",
            "intake",
            "front",
            "help",
            "claims",
            "case",
        ]
        specialist_keywords = [
            "operations",
            "inventory",
            "supply",
            "logistics",
            "clinical",
            "fraud",
            "risk",
            "finance",
            "analyst",
            "advisor",
            "planner",
            "engineer",
            "quality",
            "store",
            "production",
        ]
        reviewer_keywords = [
            "compliance",
            "audit",
            "security",
            "safety",
            "qa",
            "quality",
            "legal",
            "risk",
        ]
        analyst_keywords = [
            "analytics",
            "insight",
            "strategy",
            "forecast",
            "planning",
            "data",
        ]
        writer_keywords = [
            "marketing",
            "content",
            "copy",
            "writer",
            "communications",
            "brand",
            "campaign",
            "sales",
        ]
        editor_keywords = [
            "editor",
            "review",
            "quality",
            "qa",
            "compliance",
            "audit",
            "legal",
        ]

        templates: List[WorkflowTemplate] = []

        # Template 1: Triage -> Specialist -> Review
        exclude: set[str] = set()
        intake = pick_agent(intake_keywords, exclude)
        if intake:
            exclude.add(intake.id)
        specialist = pick_agent(specialist_keywords, exclude) or pick_agent([], exclude)
        if specialist:
            exclude.add(specialist.id)
        reviewer = pick_agent(reviewer_keywords, exclude) or pick_agent(analyst_keywords, exclude)

        roles = []
        if intake:
            roles.append(
                WorkflowRole(
                    id="intake",
                    name="Intake Triage",
                    agent_type=intake,
                )
            )
        if specialist and (not intake or specialist.id != intake.id):
            roles.append(
                WorkflowRole(
                    id="specialist",
                    name="Domain Specialist",
                    agent_type=specialist,
                )
            )
        if reviewer and reviewer.id not in {role.agent_type.id for role in roles}:
            roles.append(
                WorkflowRole(
                    id="reviewer",
                    name="Quality Review",
                    agent_type=reviewer,
                )
            )

        if roles:
            templates.append(
                WorkflowTemplate(
                    id="triage_handoff",
                    name="Triage Handoff",
                    description="Triage, route to a specialist, then validate the response.",
                    pattern="sequential",
                    roles=roles,
                )
            )

        # Template 2: Review Loop (requires at least two distinct roles)
        exclude = set()
        primary = pick_agent(specialist_keywords, exclude) or pick_agent(intake_keywords, exclude)
        if primary:
            exclude.add(primary.id)
        reviewer = pick_agent(reviewer_keywords, exclude) or pick_agent([], exclude)

        if primary and reviewer and primary.id != reviewer.id:
            templates.append(
                WorkflowTemplate(
                    id="review_loop",
                    name="Peer Review Loop",
                    description="Primary agent iterates with a reviewer until completion.",
                    pattern="review_loop",
                    roles=[
                        WorkflowRole(
                            id="primary",
                            name="Primary Resolver",
                            agent_type=primary,
                        ),
                        WorkflowRole(
                            id="reviewer",
                            name="Reviewer",
                            agent_type=reviewer,
                            instructions_suffix=(
                                "If the response is correct and complete, reply with [COMPLETE]."
                            ),
                        ),
                    ],
                )
            )

        # Template 3: Specialist -> Analyst Summary
        exclude = set()
        specialist = pick_agent(specialist_keywords, exclude) or pick_agent(intake_keywords, exclude)
        if specialist:
            exclude.add(specialist.id)
        analyst = pick_agent(analyst_keywords, exclude) or pick_agent([], exclude)

        if specialist and analyst and specialist.id != analyst.id:
            templates.append(
                WorkflowTemplate(
                    id="insight_summary",
                    name="Insight Summary",
                    description="Specialist responds, analyst distills key insights.",
                    pattern="sequential",
                    roles=[
                        WorkflowRole(
                            id="specialist",
                            name="Domain Specialist",
                            agent_type=specialist,
                        ),
                        WorkflowRole(
                            id="analyst",
                            name="Insight Analyst",
                            agent_type=analyst,
                        ),
                    ],
                )
            )

        # Template 4: Shared Conversation Chain
        exclude = set()
        analyst = pick_agent(analyst_keywords, exclude) or pick_agent(intake_keywords, exclude)
        if analyst:
            exclude.add(analyst.id)
        writer = pick_agent(writer_keywords, exclude) or pick_agent(specialist_keywords, exclude)
        if writer:
            exclude.add(writer.id)
        editor = pick_agent(editor_keywords, exclude) or pick_agent(reviewer_keywords, exclude)

        roles = []
        if analyst:
            roles.append(
                WorkflowRole(
                    id="analyst",
                    name="Analysis Lead",
                    agent_type=analyst,
                )
            )
        if writer and writer.id not in {role.agent_type.id for role in roles}:
            roles.append(
                WorkflowRole(
                    id="writer",
                    name="Content Drafter",
                    agent_type=writer,
                )
            )
        if editor and editor.id not in {role.agent_type.id for role in roles}:
            roles.append(
                WorkflowRole(
                    id="editor",
                    name="Final Editor",
                    agent_type=editor,
                )
            )

        if len(roles) >= 2:
            templates.append(
                WorkflowTemplate(
                    id="shared_conversation_chain",
                    name="Shared Conversation Chain",
                    description="Sequential handoff using a single conversation thread.",
                    pattern="sequential_shared",
                    roles=roles,
                )
            )

        # Template 5: Human Confirmation Gate
        templates.append(
            WorkflowTemplate(
                id="human_confirmation",
                name="Human Confirmation Gate",
                description="Request a user confirmation before continuing.",
                pattern="human_in_loop",
                roles=[],
            )
        )

        # Template 6: Group Chat Loop
        exclude = set()
        speaker = pick_agent(intake_keywords, exclude) or pick_agent(specialist_keywords, exclude)
        if speaker:
            exclude.add(speaker.id)
        moderator = pick_agent(reviewer_keywords, exclude) or pick_agent(analyst_keywords, exclude)
        if speaker and moderator and speaker.id != moderator.id:
            templates.append(
                WorkflowTemplate(
                    id="group_chat_loop",
                    name="Group Chat Loop",
                    description="Two agents iterate until completion or timeout.",
                    pattern="group_chat",
                    roles=[
                        WorkflowRole(
                            id="speaker",
                            name="Primary Speaker",
                            agent_type=speaker,
                        ),
                        WorkflowRole(
                            id="moderator",
                            name="Moderator",
                            agent_type=moderator,
                            instructions_suffix="Conclude with [COMPLETE] when the answer is final.",
                        ),
                    ],
                )
            )

        return templates

    def create_workflows_from_profile(
        self,
        profile: IndustryProfile,
        template_ids: List[str],
        workflows_per_template: int,
        org_count: int = 1,
        models: Optional[List[str]] = None,
        progress_callback=None,
    ) -> WorkflowBatchResult:
        """
        Create workflow agents based on an industry profile.

        Args:
            profile: Industry profile defining agent types
            template_ids: List of workflow template IDs to create
            workflows_per_template: Number of workflows to create per template per org
            org_count: Number of organizations to create workflows for
            models: List of models to randomly assign (required)
            progress_callback: Optional callback(current, total, message)

        Returns:
            WorkflowBatchResult with created and failed workflows
        """
        result = WorkflowBatchResult()
        available_models = models or self.models

        if not profile:
            raise ValueError("No industry profile selected. Please select a profile first.")

        if not available_models:
            raise ValueError("No models provided. Please select models from your Microsoft Foundry project.")

        templates = [t for t in self.build_templates(profile) if t.id in template_ids]
        if not templates:
            raise ValueError("No workflow templates selected. Please select at least one template.")

        client = get_project_client()

        total_units = 0
        for template in templates:
            total_units += (len(template.roles) + 1) * workflows_per_template * org_count
        current_units = 0

        def update_progress(message: str) -> None:
            if progress_callback:
                progress_callback(current_units, total_units, message)

        for org_num in range(1, org_count + 1):
            org_id = f"{profile.organization.prefix}{org_num:03d}"

            for template in templates:
                for workflow_index in range(1, workflows_per_template + 1):
                    workflow_name = self._build_workflow_name(
                        org_id,
                        template.id,
                        workflow_index,
                    )
                    try:
                        role_agents: Dict[str, str] = {}
                        for role_index, role in enumerate(template.roles, start=1):
                            agent_name = self._build_workflow_agent_name(
                                org_id,
                                template.id,
                                workflow_index,
                                role.id,
                                role_index,
                            )
                            instructions = self._build_role_instructions(role)
                            selected_model = random.choice(available_models)

                            update_progress(f"Creating agent {agent_name}...")
                            agent = client.agents.create_version(
                                agent_name=agent_name,
                                definition=PromptAgentDefinition(
                                    model=selected_model,
                                    instructions=instructions,
                                ),
                            )
                            role_agents[role.id] = agent.name
                            current_units += 1

                        workflow_yaml = self._build_workflow_yaml(template, role_agents)
                        update_progress(f"Creating workflow {workflow_name}...")
                        workflow = client.agents.create_version(
                            agent_name=workflow_name,
                            definition=WorkflowAgentDefinition(workflow=workflow_yaml),
                        )
                        current_units += 1

                        result.created.append(
                            CreatedWorkflow(
                                name=workflow.name,
                                azure_id=workflow.id,
                                version=workflow.version,
                                org_id=org_id,
                                template_id=template.id,
                                template_name=template.name,
                                agent_names=list(role_agents.values()),
                            )
                        )

                    except Exception as e:
                        current_units += 1
                        result.failed.append(
                            {
                                "workflow_name": workflow_name,
                                "template_id": template.id,
                                "org_id": org_id,
                                "error": str(e),
                            }
                        )

        current_units = total_units
        update_progress("Workflow creation completed.")
        return result

    def _build_role_instructions(self, role: WorkflowRole) -> str:
        base = (role.agent_type.instructions or "").strip()
        if role.instructions_suffix:
            return f"{base}\n\n{role.instructions_suffix}"
        return base

    def _build_workflow_name(self, org_id: str, template_id: str, workflow_index: int) -> str:
        template_slug = template_id.replace("_", "-")
        return f"{org_id}-WF-{template_slug}-{workflow_index:03d}"

    def _build_workflow_agent_name(
        self,
        org_id: str,
        template_id: str,
        workflow_index: int,
        role_id: str,
        role_index: int,
    ) -> str:
        role_slug = self._slugify(role_id)
        template_slug = template_id.replace("_", "-")
        return f"{org_id}-WF-{template_slug}-{workflow_index:03d}-{role_slug}-{role_index:02d}"

    def _build_workflow_yaml(self, template: WorkflowTemplate, role_agents: Dict[str, str]) -> str:
        if template.pattern == "review_loop":
            return self._build_review_loop_yaml(template, role_agents)
        if template.pattern == "group_chat":
            return self._build_group_chat_yaml(template, role_agents)
        if template.pattern == "human_in_loop":
            return self._build_human_in_loop_yaml()
        if template.pattern == "sequential_shared":
            return self._build_shared_conversation_sequential_yaml(template, role_agents)
        return self._build_sequential_yaml(template, role_agents)

    def _build_sequential_yaml(self, template: WorkflowTemplate, role_agents: Dict[str, str]) -> str:
        lines = [
            "kind: workflow",
            "trigger:",
            "  kind: OnConversationStart",
            "  id: workflow_start",
            "  actions:",
            "    - kind: SetVariable",
            "      id: set_variable_input",
            "      variable: Local.LatestMessage",
            "      value: \"=UserMessage(System.LastMessageText)\"",
        ]

        for role in template.roles:
            role_key = self._slugify(role.id)
            conversation_var = self._conversation_var(role_key)
            agent_name = role_agents.get(role.id, "")

            lines.extend(
                [
                    "    - kind: CreateConversation",
                    f"      id: create_{role_key}_conversation",
                    f"      conversationId: {conversation_var}",
                    "    - kind: InvokeAzureAgent",
                    f"      id: {role_key}_agent",
                    f"      description: {role.name}",
                    f"      conversationId: \"={conversation_var}\"",
                    "      agent:",
                    f"        name: {agent_name}",
                    "      input:",
                    "        messages: \"=Local.LatestMessage\"",
                    "      output:",
                    "        messages: Local.LatestMessage",
                ]
            )

        lines.extend(
            [
                "    - kind: EndConversation",
                "      id: end_workflow",
            ]
        )

        return "\n".join(lines)

    def _build_shared_conversation_sequential_yaml(
        self,
        template: WorkflowTemplate,
        role_agents: Dict[str, str],
    ) -> str:
        lines = [
            "kind: workflow",
            "trigger:",
            "  kind: OnConversationStart",
            "  id: workflow_start",
            "  actions:",
        ]

        for index, role in enumerate(template.roles):
            role_key = self._slugify(role.id)
            agent_name = role_agents.get(role.id, "")
            input_source = "=System.LastMessage" if index == 0 else "=Local.LatestMessage"

            lines.extend(
                [
                    "    - kind: InvokeAzureAgent",
                    f"      id: {role_key}_agent",
                    f"      description: {role.name}",
                    "      conversationId: \"=System.ConversationId\"",
                    "      agent:",
                    f"        name: {agent_name}",
                    "      input:",
                    f"        messages: \"{input_source}\"",
                    "      output:",
                    "        messages: Local.LatestMessage",
                    "        autoSend: true",
                ]
            )

        lines.extend(
            [
                "    - kind: EndConversation",
                "      id: end_workflow",
            ]
        )

        return "\n".join(lines)

    def _build_review_loop_yaml(self, template: WorkflowTemplate, role_agents: Dict[str, str]) -> str:
        if len(template.roles) < 2:
            return self._build_sequential_yaml(template, role_agents)

        primary = template.roles[0]
        reviewer = template.roles[1]
        primary_key = self._slugify(primary.id)
        reviewer_key = self._slugify(reviewer.id)
        primary_var = self._conversation_var(primary_key)
        reviewer_var = self._conversation_var(reviewer_key)

        lines = [
            "kind: workflow",
            "trigger:",
            "  kind: OnConversationStart",
            "  id: workflow_start",
            "  actions:",
            "    - kind: SetVariable",
            "      id: set_variable_input",
            "      variable: Local.LatestMessage",
            "      value: \"=UserMessage(System.LastMessageText)\"",
            "    - kind: SetVariable",
            "      id: set_variable_turncount",
            "      variable: Local.TurnCount",
            "      value: \"=0\"",
            "    - kind: CreateConversation",
            f"      id: create_{primary_key}_conversation",
            f"      conversationId: {primary_var}",
            "    - kind: CreateConversation",
            f"      id: create_{reviewer_key}_conversation",
            f"      conversationId: {reviewer_var}",
            "    - kind: InvokeAzureAgent",
            f"      id: {primary_key}_agent",
            f"      description: {primary.name}",
            f"      conversationId: \"={primary_var}\"",
            "      agent:",
            f"        name: {role_agents.get(primary.id, '')}",
            "      input:",
            "        messages: \"=Local.LatestMessage\"",
            "      output:",
            "        messages: Local.LatestMessage",
            "    - kind: InvokeAzureAgent",
            f"      id: {reviewer_key}_agent",
            f"      description: {reviewer.name}",
            f"      conversationId: \"={reviewer_var}\"",
            "      agent:",
            f"        name: {role_agents.get(reviewer.id, '')}",
            "      input:",
            "        messages: \"=Local.LatestMessage\"",
            "      output:",
            "        messages: Local.LatestMessage",
            "    - kind: SetVariable",
            "      id: increment_turncount",
            "      variable: Local.TurnCount",
            "      value: \"=Local.TurnCount + 1\"",
            "    - kind: ConditionGroup",
            "      id: completion_check",
            "      conditions:",
            "        - condition: '=!IsBlank(Find(\"[COMPLETE]\", Upper(Last(Local.LatestMessage).Text)))'",
            "          id: check_done",
            "          actions:",
            "            - kind: EndConversation",
            "              id: end_workflow",
            "        - condition: \"=Local.TurnCount >= 4\"",
            "          id: check_turn_count_exceeded",
            "          actions:",
            "            - kind: SendActivity",
            "              id: send_activity_tired",
            "              activity: \"Let's try again later.\"",
            "      elseActions:",
            "        - kind: GotoAction",
            "          id: goto_primary_agent",
            f"          actionId: {primary_key}_agent",
        ]

        return "\n".join(lines)

    def _build_group_chat_yaml(self, template: WorkflowTemplate, role_agents: Dict[str, str]) -> str:
        if len(template.roles) < 2:
            return self._build_sequential_yaml(template, role_agents)

        speaker = template.roles[0]
        moderator = template.roles[1]
        speaker_key = self._slugify(speaker.id)
        moderator_key = self._slugify(moderator.id)

        lines = [
            "kind: workflow",
            "trigger:",
            "  kind: OnConversationStart",
            "  id: workflow_start",
            "  actions:",
            "    - kind: SetVariable",
            "      id: set_variable_input",
            "      variable: Local.LatestMessage",
            "      value: \"=UserMessage(System.LastMessageText)\"",
            "    - kind: SetVariable",
            "      id: set_variable_turncount",
            "      variable: Local.TurnCount",
            "      value: \"=0\"",
            "    - kind: InvokeAzureAgent",
            f"      id: {speaker_key}_agent",
            f"      description: {speaker.name}",
            "      conversationId: \"=System.ConversationId\"",
            "      agent:",
            f"        name: {role_agents.get(speaker.id, '')}",
            "      input:",
            "        messages: \"=Local.LatestMessage\"",
            "      output:",
            "        messages: Local.LatestMessage",
            "        autoSend: true",
            "    - kind: InvokeAzureAgent",
            f"      id: {moderator_key}_agent",
            f"      description: {moderator.name}",
            "      conversationId: \"=System.ConversationId\"",
            "      agent:",
            f"        name: {role_agents.get(moderator.id, '')}",
            "      input:",
            "        messages: \"=Local.LatestMessage\"",
            "      output:",
            "        messages: Local.LatestMessage",
            "        autoSend: true",
            "    - kind: SetVariable",
            "      id: increment_turncount",
            "      variable: Local.TurnCount",
            "      value: \"=Local.TurnCount + 1\"",
            "    - kind: ConditionGroup",
            "      id: completion_check",
            "      conditions:",
            "        - condition: '=!IsBlank(Find(\"[COMPLETE]\", Upper(Last(Local.LatestMessage).Text)))'",
            "          id: check_done",
            "          actions:",
            "            - kind: EndConversation",
            "              id: end_workflow",
            "        - condition: \"=Local.TurnCount >= 4\"",
            "          id: check_turn_count_exceeded",
            "          actions:",
            "            - kind: SendActivity",
            "              id: send_activity_tired",
            "              activity: \"Let's try again later...I am tired.\"",
            "      elseActions:",
            "        - kind: GotoAction",
            "          id: goto_speaker_agent",
            f"          actionId: {speaker_key}_agent",
        ]

        return "\n".join(lines)

    def _build_human_in_loop_yaml(self) -> str:
        lines = [
            "kind: workflow",
            "trigger:",
            "  kind: OnConversationStart",
            "  id: workflow_start",
            "  actions:",
            "    - kind: SetVariable",
            "      id: set_original_input",
            "      variable: Local.OriginalInput",
            "      value: \"=System.LastMessageText\"",
            "    - kind: Question",
            "      id: question_confirm",
            "      variable: Local.ConfirmedInput",
            "      prompt: \"CONFIRM: Please re-enter your input to confirm\"",
            "      entity: StringPrebuiltEntity",
            "      alwaysPrompt: false",
            "    - kind: ConditionGroup",
            "      id: check_completion",
            "      conditions:",
            "        - id: check_confirm",
            "          condition: \"=Local.OriginalInput <> Local.ConfirmedInput\"",
            "          actions:",
            "            - kind: SendActivity",
            "              id: send_activity_mismatch",
            "              activity: '\"{Local.ConfirmedInput}\" does not match the original input of \"{Local.OriginalInput}\". Please try again.'",
            "            - kind: GotoAction",
            "              id: goto_again",
            "              actionId: question_confirm",
            "      elseActions:",
            "        - kind: SendActivity",
            "          id: send_activity_confirmed",
            "          activity: |-",
            "            You entered:",
            "                {Local.OriginalInput}",
            "            ",
            "            Confirmed input:",
            "                {Local.ConfirmedInput}",
            "    - kind: EndConversation",
            "      id: end_workflow",
        ]

        return "\n".join(lines)

    def _slugify(self, value: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
        return slug or "role"

    def _conversation_var(self, role_key: str) -> str:
        return f"Local.{role_key.title().replace('_', '')}ConversationId"
