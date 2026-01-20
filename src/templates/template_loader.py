"""
Template loader for Microsoft Foundry Agent Toolkit.

Loads and validates industry profile YAML templates with:
- YAML parsing with error handling
- Pydantic model validation
- Template discovery and listing
- Default template merging
"""

import os
from pathlib import Path
from typing import List, Optional, Dict, Any
import yaml

from ..models.industry_profile import (
    IndustryProfile,
    ProfileMetadata,
    OrganizationConfig,
    DepartmentConfig,
    ModelConfig,
    AgentType,
    GuardrailTests,
    DaemonProfileConfig,
)


# Default templates directory
DEFAULT_TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates" / "industries"


class TemplateLoadError(Exception):
    """Error loading or parsing a template."""
    pass


class TemplateValidationError(Exception):
    """Error validating template structure."""
    pass


class TemplateLoader:
    """
    Loader for industry profile YAML templates.

    Discovers, loads, and validates templates from the templates directory.
    """

    def __init__(self, templates_dir: str = None):
        """
        Initialize the template loader.

        Args:
            templates_dir: Directory containing YAML templates
        """
        self.templates_dir = Path(templates_dir) if templates_dir else DEFAULT_TEMPLATES_DIR
        self._cache: Dict[str, IndustryProfile] = {}

    def list_templates(self) -> List[str]:
        """
        List available template names.

        Returns:
            List of template IDs (filename without extension)
        """
        templates = []

        if not self.templates_dir.exists():
            return templates

        for path in self.templates_dir.glob("*.yaml"):
            templates.append(path.stem)

        for path in self.templates_dir.glob("*.yml"):
            templates.append(path.stem)

        return sorted(set(templates))

    def get_template_path(self, template_id: str) -> Optional[Path]:
        """
        Get the path to a template file.

        Args:
            template_id: Template identifier (filename without extension)

        Returns:
            Path to the template file or None if not found
        """
        for ext in [".yaml", ".yml"]:
            path = self.templates_dir / f"{template_id}{ext}"
            if path.exists():
                return path
        return None

    def load_yaml(self, template_id: str) -> Dict[str, Any]:
        """
        Load raw YAML content from a template file.

        Args:
            template_id: Template identifier

        Returns:
            Dictionary of parsed YAML content

        Raises:
            TemplateLoadError: If file not found or YAML parsing fails
        """
        path = self.get_template_path(template_id)

        if path is None:
            raise TemplateLoadError(f"Template not found: {template_id}")

        try:
            with open(path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise TemplateLoadError(f"YAML parsing error in {template_id}: {e}")
        except IOError as e:
            raise TemplateLoadError(f"Error reading {template_id}: {e}")

    def load_template(self, template_id: str, use_cache: bool = True) -> IndustryProfile:
        """
        Load and validate an industry profile template.

        Args:
            template_id: Template identifier
            use_cache: Whether to use cached templates

        Returns:
            Validated IndustryProfile object

        Raises:
            TemplateLoadError: If loading fails
            TemplateValidationError: If validation fails
        """
        if use_cache and template_id in self._cache:
            return self._cache[template_id]

        data = self.load_yaml(template_id)

        try:
            profile = self._parse_profile(data)
            self._cache[template_id] = profile
            return profile
        except Exception as e:
            raise TemplateValidationError(f"Validation error in {template_id}: {e}")

    def _parse_profile(self, data: Dict[str, Any]) -> IndustryProfile:
        """
        Parse raw YAML data into an IndustryProfile.

        Args:
            data: Raw YAML dictionary

        Returns:
            IndustryProfile object
        """
        # Parse metadata
        metadata_data = data.get("metadata", {})
        metadata = ProfileMetadata(
            id=metadata_data.get("id", "unknown"),
            name=metadata_data.get("name", "Unknown Profile"),
            description=metadata_data.get("description"),
            version=metadata_data.get("version", "1.0.0"),
        )

        # Parse organization
        org_data = data.get("organization", {})
        departments = [
            DepartmentConfig(name=d["name"], code=d["code"])
            for d in org_data.get("departments", [])
        ]
        organization = OrganizationConfig(
            prefix=org_data.get("prefix", "ORG"),
            departments=departments,
        )

        # Parse models
        models_data = data.get("models", {})
        models = ModelConfig(
            preferred=models_data.get("preferred", []),
            allowed=models_data.get("allowed", []),
        )

        # Parse agent types
        agent_types = []
        for at_data in data.get("agent_types", []):
            agent_type = AgentType(
                id=at_data["id"],
                name=at_data["name"],
                department=at_data.get("department", ""),
                description=at_data.get("description"),
                instructions=at_data.get("instructions", ""),
                tools=at_data.get("tools", []),
                query_templates=at_data.get("query_templates", []),
            )
            agent_types.append(agent_type)

        # Parse guardrail tests
        gt_data = data.get("guardrail_tests", {})
        guardrail_tests = GuardrailTests(
            harms_content=gt_data.get("harms_content", []),
            jailbreak_content=gt_data.get("jailbreak_content", []),
            indirect_prompt_injection=gt_data.get("indirect_prompt_injection", []),
            self_harm_content=gt_data.get("self_harm_content", []),
            sexual_content=gt_data.get("sexual_content", []),
            pii_exposure=gt_data.get("pii_exposure", []),
            data_exfiltration=gt_data.get("data_exfiltration", []),
        )

        # Parse daemon config
        dc_data = data.get("daemon_config", {})
        target_daily = dc_data.get("target_daily_requests", {})
        daemon_config = DaemonProfileConfig(
            target_daily_requests={
                "min": target_daily.get("min", 3000),
                "max": target_daily.get("max", 5000),
            },
            execution_interval_minutes=dc_data.get("execution_interval_minutes", 15),
            simulation_mix=dc_data.get("simulation_mix", {
                "operations_weight": 70,
                "guardrails_weight": 30,
            }),
            load_profiles=dc_data.get("load_profiles"),
        )

        return IndustryProfile(
            metadata=metadata,
            organization=organization,
            models=models,
            agent_types=agent_types,
            guardrail_tests=guardrail_tests,
            daemon_config=daemon_config,
        )

    def load_all_templates(self) -> Dict[str, IndustryProfile]:
        """
        Load all available templates.

        Returns:
            Dictionary mapping template ID to IndustryProfile
        """
        templates = {}
        for template_id in self.list_templates():
            try:
                templates[template_id] = self.load_template(template_id)
            except (TemplateLoadError, TemplateValidationError) as e:
                print(f"Warning: Could not load template {template_id}: {e}")
        return templates

    def get_template_info(self, template_id: str) -> Dict[str, Any]:
        """
        Get summary information about a template.

        Args:
            template_id: Template identifier

        Returns:
            Dictionary with template summary
        """
        profile = self.load_template(template_id)
        return {
            "id": profile.metadata.id,
            "name": profile.metadata.name,
            "description": profile.metadata.description,
            "version": profile.metadata.version,
            "agent_types": len(profile.agent_types),
            "departments": len(profile.organization.departments),
            "models": len(profile.models.allowed),
        }

    def save_template(self, profile: IndustryProfile, template_id: str = None) -> Path:
        """
        Save an industry profile to a YAML file.

        Args:
            profile: IndustryProfile to save
            template_id: Optional template ID (uses profile.metadata.id if not provided)

        Returns:
            Path to the saved file
        """
        template_id = template_id or profile.metadata.id
        path = self.templates_dir / f"{template_id}.yaml"

        # Ensure directory exists
        self.templates_dir.mkdir(parents=True, exist_ok=True)

        # Convert to dictionary
        data = self._profile_to_dict(profile)

        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        # Invalidate cache
        if template_id in self._cache:
            del self._cache[template_id]

        return path

    def _profile_to_dict(self, profile: IndustryProfile) -> Dict[str, Any]:
        """Convert an IndustryProfile to a dictionary for YAML export."""
        return {
            "metadata": {
                "id": profile.metadata.id,
                "name": profile.metadata.name,
                "description": profile.metadata.description,
                "version": profile.metadata.version,
            },
            "organization": {
                "prefix": profile.organization.prefix,
                "departments": [
                    {"name": d.name, "code": d.code}
                    for d in profile.organization.departments
                ],
            },
            "models": {
                "preferred": profile.models.preferred,
                "allowed": profile.models.allowed,
            },
            "agent_types": [
                {
                    "id": at.id,
                    "name": at.name,
                    "department": at.department,
                    "description": at.description,
                    "instructions": at.instructions,
                    "tools": at.tools,
                    "query_templates": at.query_templates,
                }
                for at in profile.agent_types
            ],
            "guardrail_tests": profile.guardrail_tests.get_non_empty_categories(),
            "daemon_config": {
                "target_daily_requests": profile.daemon_config.target_daily_requests,
                "execution_interval_minutes": profile.daemon_config.execution_interval_minutes,
                "simulation_mix": profile.daemon_config.simulation_mix,
                "load_profiles": profile.daemon_config.load_profiles,
            },
        }

    def clear_cache(self) -> None:
        """Clear the template cache."""
        self._cache.clear()


# Convenience functions
def load_template(template_id: str) -> IndustryProfile:
    """Load a template by ID."""
    return TemplateLoader().load_template(template_id)


def list_available_templates() -> List[str]:
    """List available template IDs."""
    return TemplateLoader().list_templates()


def get_template_summary(template_id: str) -> Dict[str, Any]:
    """Get summary info for a template."""
    return TemplateLoader().get_template_info(template_id)
