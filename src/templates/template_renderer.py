"""
Template renderer for Microsoft Foundry Agent Toolkit.

Renders Jinja2 templates for code generation:
- Simulation script generation
- Guardrail test generation
- Daemon configuration generation
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..models.industry_profile import IndustryProfile
from ..models.simulation_config import DaemonConfig


# Default code templates directory
DEFAULT_CODE_TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates" / "code"


class TemplateRenderError(Exception):
    """Error rendering a template."""
    pass


class TemplateRenderer:
    """
    Renderer for Jinja2 code templates.

    Generates simulation scripts and configurations from industry profiles.
    """

    def __init__(self, templates_dir: str = None):
        """
        Initialize the template renderer.

        Args:
            templates_dir: Directory containing Jinja2 templates
        """
        self.templates_dir = Path(templates_dir) if templates_dir else DEFAULT_CODE_TEMPLATES_DIR

        # Ensure templates directory exists
        self.templates_dir.mkdir(parents=True, exist_ok=True)

        # Initialize Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Add custom filters
        self.env.filters['quote'] = lambda s: f'"{s}"'
        self.env.filters['python_list'] = self._python_list_filter

    def _python_list_filter(self, items: list) -> str:
        """Convert a list to Python list syntax."""
        if not items:
            return "[]"
        quoted = [f'"{item}"' for item in items]
        return f"[{', '.join(quoted)}]"

    def render_template(
        self,
        template_name: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Render a Jinja2 template with the given context.

        Args:
            template_name: Name of the template file
            context: Dictionary of template variables

        Returns:
            Rendered template string

        Raises:
            TemplateRenderError: If rendering fails
        """
        try:
            template = self.env.get_template(template_name)
            return template.render(**context)
        except Exception as e:
            raise TemplateRenderError(f"Error rendering {template_name}: {e}")

    def render_operations_script(
        self,
        profile: IndustryProfile,
        endpoint: str = None,
        output_path: str = None
    ) -> str:
        """
        Render the operations simulation script.

        Args:
            profile: Industry profile
            endpoint: Azure endpoint (uses default if not provided)
            output_path: Optional output file path

        Returns:
            Rendered Python script
        """
        context = {
            "profile": profile,
            "endpoint": endpoint or os.environ.get("PROJECT_ENDPOINT", ""),
            "generation_timestamp": datetime.now().isoformat(),
            "query_templates": profile.get_query_templates_dict(),
        }

        content = self.render_template("simulate_operations.py.j2", context)

        if output_path:
            self._write_file(output_path, content)

        return content

    def render_guardrails_script(
        self,
        profile: IndustryProfile,
        endpoint: str = None,
        output_path: str = None
    ) -> str:
        """
        Render the guardrail testing script.

        Args:
            profile: Industry profile
            endpoint: Azure endpoint
            output_path: Optional output file path

        Returns:
            Rendered Python script
        """
        context = {
            "profile": profile,
            "endpoint": endpoint or os.environ.get("PROJECT_ENDPOINT", ""),
            "generation_timestamp": datetime.now().isoformat(),
            "guardrail_tests": profile.guardrail_tests.get_non_empty_categories(),
        }

        content = self.render_template("simulate_guardrails.py.j2", context)

        if output_path:
            self._write_file(output_path, content)

        return content

    def render_daemon_config(
        self,
        profile: IndustryProfile,
        daemon_config: DaemonConfig = None,
        agents_csv: str = "created_agents_results.csv",
        output_path: str = None
    ) -> str:
        """
        Render the daemon configuration JSON.

        Args:
            profile: Industry profile
            daemon_config: Optional custom daemon config (uses profile default if not provided)
            agents_csv: Path to agents CSV file
            output_path: Optional output file path

        Returns:
            Rendered JSON configuration
        """
        context = {
            "profile": profile,
            "daemon_config": daemon_config,
            "agents_csv": agents_csv,
            "generation_timestamp": datetime.now().isoformat(),
        }

        content = self.render_template("daemon_config.json.j2", context)

        if output_path:
            self._write_file(output_path, content)

        return content

    def render_all(
        self,
        profile: IndustryProfile,
        output_dir: str,
        endpoint: str = None,
        agents_csv: str = "created_agents_results.csv"
    ) -> Dict[str, str]:
        """
        Render all code templates for a profile.

        Args:
            profile: Industry profile
            output_dir: Output directory for generated files
            endpoint: Azure endpoint
            agents_csv: Path to agents CSV

        Returns:
            Dictionary mapping filename to content
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        results = {}

        # Operations script
        ops_path = output_path / "simulate_agent_operations.py"
        results["simulate_agent_operations.py"] = self.render_operations_script(
            profile, endpoint, str(ops_path)
        )

        # Guardrails script
        guard_path = output_path / "simulate_guardrail_testing.py"
        results["simulate_guardrail_testing.py"] = self.render_guardrails_script(
            profile, endpoint, str(guard_path)
        )

        # Daemon config
        config_path = output_path / "simulation_daemon_config.json"
        results["simulation_daemon_config.json"] = self.render_daemon_config(
            profile, agents_csv=agents_csv, output_path=str(config_path)
        )

        return results

    def _write_file(self, path: str, content: str) -> None:
        """Write content to a file."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

    def has_template(self, template_name: str) -> bool:
        """Check if a template exists."""
        return (self.templates_dir / template_name).exists()

    def list_templates(self) -> list:
        """List available Jinja2 templates."""
        if not self.templates_dir.exists():
            return []
        return [p.name for p in self.templates_dir.glob("*.j2")]


# Convenience functions
def render_code(
    profile: IndustryProfile,
    output_dir: str,
    endpoint: str = None
) -> Dict[str, str]:
    """
    Render all code templates for a profile.

    Args:
        profile: Industry profile
        output_dir: Output directory
        endpoint: Azure endpoint

    Returns:
        Dictionary of rendered files
    """
    return TemplateRenderer().render_all(profile, output_dir, endpoint)
