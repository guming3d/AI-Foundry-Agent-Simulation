"""
Main code generator orchestrator for Microsoft Foundry Agent Toolkit.

Coordinates generation of all simulation artifacts from industry profiles.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from ..models.industry_profile import IndustryProfile
from ..templates.template_loader import TemplateLoader
from ..templates.template_renderer import TemplateRenderer


class CodeGeneratorConfig:
    """Configuration for code generation."""

    def __init__(
        self,
        output_dir: str = "output/generated_code",
        agents_csv: str = "created_agents_results.csv",
        endpoint: str = None,
    ):
        self.output_dir = output_dir
        self.agents_csv = agents_csv
        self.endpoint = endpoint or os.environ.get("PROJECT_ENDPOINT", "")


class GeneratedArtifact:
    """Represents a generated code artifact."""

    def __init__(self, name: str, path: str, content: str, artifact_type: str):
        self.name = name
        self.path = path
        self.content = content
        self.artifact_type = artifact_type
        self.generated_at = datetime.now()

    def __repr__(self):
        return f"GeneratedArtifact({self.name}, type={self.artifact_type})"


class CodeGenerator:
    """
    Main code generator for Microsoft Foundry Agent Toolkit.

    Generates all simulation code artifacts from industry profiles:
    - Operations simulation script
    - Guardrail testing script
    - Daemon configuration
    """

    def __init__(self, config: CodeGeneratorConfig = None):
        """
        Initialize the code generator.

        Args:
            config: Optional configuration object
        """
        self.config = config or CodeGeneratorConfig()
        self.template_loader = TemplateLoader()
        self.template_renderer = TemplateRenderer()
        self.artifacts: List[GeneratedArtifact] = []

    def generate_all(
        self,
        profile: IndustryProfile,
        output_dir: str = None,
    ) -> Dict[str, GeneratedArtifact]:
        """
        Generate all code artifacts for an industry profile.

        Args:
            profile: Industry profile to generate code for
            output_dir: Optional output directory override

        Returns:
            Dictionary mapping filename to GeneratedArtifact
        """
        output_path = Path(output_dir or self.config.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        results = {}

        # Generate operations script
        ops_artifact = self.generate_operations_script(profile, output_path)
        results[ops_artifact.name] = ops_artifact

        # Generate guardrails script
        guard_artifact = self.generate_guardrails_script(profile, output_path)
        results[guard_artifact.name] = guard_artifact

        # Generate daemon config
        config_artifact = self.generate_daemon_config(profile, output_path)
        results[config_artifact.name] = config_artifact

        self.artifacts.extend(results.values())

        return results

    def generate_operations_script(
        self,
        profile: IndustryProfile,
        output_path: Path,
    ) -> GeneratedArtifact:
        """Generate the operations simulation script."""
        content = self.template_renderer.render_operations_script(
            profile=profile,
            endpoint=self.config.endpoint,
        )

        filename = "simulate_agent_operations.py"
        filepath = output_path / filename

        self._write_file(filepath, content)

        return GeneratedArtifact(
            name=filename,
            path=str(filepath),
            content=content,
            artifact_type="operations_script",
        )

    def generate_guardrails_script(
        self,
        profile: IndustryProfile,
        output_path: Path,
    ) -> GeneratedArtifact:
        """Generate the guardrail testing script."""
        content = self.template_renderer.render_guardrails_script(
            profile=profile,
            endpoint=self.config.endpoint,
        )

        filename = "simulate_guardrail_testing.py"
        filepath = output_path / filename

        self._write_file(filepath, content)

        return GeneratedArtifact(
            name=filename,
            path=str(filepath),
            content=content,
            artifact_type="guardrails_script",
        )

    def generate_daemon_config(
        self,
        profile: IndustryProfile,
        output_path: Path,
    ) -> GeneratedArtifact:
        """Generate the daemon configuration JSON."""
        content = self.template_renderer.render_daemon_config(
            profile=profile,
            agents_csv=self.config.agents_csv,
        )

        filename = "simulation_daemon_config.json"
        filepath = output_path / filename

        self._write_file(filepath, content)

        return GeneratedArtifact(
            name=filename,
            path=str(filepath),
            content=content,
            artifact_type="daemon_config",
        )

    def generate_from_template_id(
        self,
        template_id: str,
        output_dir: str = None,
    ) -> Dict[str, GeneratedArtifact]:
        """
        Generate code from a template ID.

        Args:
            template_id: ID of the industry template
            output_dir: Optional output directory

        Returns:
            Dictionary of generated artifacts
        """
        profile = self.template_loader.load_template(template_id)
        return self.generate_all(profile, output_dir)

    def _write_file(self, path: Path, content: str) -> None:
        """Write content to a file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

    def get_generation_summary(self) -> Dict[str, Any]:
        """Get a summary of all generated artifacts."""
        return {
            "total_artifacts": len(self.artifacts),
            "artifacts": [
                {
                    "name": a.name,
                    "path": a.path,
                    "type": a.artifact_type,
                    "generated_at": a.generated_at.isoformat(),
                }
                for a in self.artifacts
            ],
        }


def generate_code_for_profile(
    profile: IndustryProfile,
    output_dir: str = "output/generated_code",
    agents_csv: str = "created_agents_results.csv",
    endpoint: str = None,
) -> Dict[str, str]:
    """
    Convenience function to generate all code for a profile.

    Args:
        profile: Industry profile
        output_dir: Output directory
        agents_csv: Path to agents CSV
        endpoint: Azure endpoint

    Returns:
        Dictionary mapping filename to file path
    """
    config = CodeGeneratorConfig(
        output_dir=output_dir,
        agents_csv=agents_csv,
        endpoint=endpoint,
    )

    generator = CodeGenerator(config)
    artifacts = generator.generate_all(profile)

    return {name: artifact.path for name, artifact in artifacts.items()}


def generate_code_for_template(
    template_id: str,
    output_dir: str = "output/generated_code",
    agents_csv: str = "created_agents_results.csv",
    endpoint: str = None,
) -> Dict[str, str]:
    """
    Convenience function to generate all code from a template ID.

    Args:
        template_id: Industry template ID (e.g., 'retail', 'healthcare')
        output_dir: Output directory
        agents_csv: Path to agents CSV
        endpoint: Azure endpoint

    Returns:
        Dictionary mapping filename to file path
    """
    config = CodeGeneratorConfig(
        output_dir=output_dir,
        agents_csv=agents_csv,
        endpoint=endpoint,
    )

    generator = CodeGenerator(config)
    artifacts = generator.generate_from_template_id(template_id)

    return {name: artifact.path for name, artifact in artifacts.items()}
