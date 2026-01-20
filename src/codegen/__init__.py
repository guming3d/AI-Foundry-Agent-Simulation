"""
Code generation engine for Microsoft Foundry Agent Toolkit.

This module provides:
- Simulation script generation
- Guardrail test generation
- Daemon configuration generation
- Visualization script generation
"""

from .generator import (
    CodeGenerator,
    CodeGeneratorConfig,
    GeneratedArtifact,
    generate_code_for_profile,
    generate_code_for_template,
)

__all__ = [
    "CodeGenerator",
    "CodeGeneratorConfig",
    "GeneratedArtifact",
    "generate_code_for_profile",
    "generate_code_for_template",
]
