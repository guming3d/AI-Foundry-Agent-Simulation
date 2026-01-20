"""
Template management for Microsoft Foundry Agent Toolkit.

This module provides:
- YAML template loading and validation
- Jinja2-based code rendering
- Template merging and customization
"""

from .template_loader import (
    TemplateLoader,
    TemplateLoadError,
    TemplateValidationError,
    load_template,
    list_available_templates,
    get_template_summary,
)
from .template_renderer import (
    TemplateRenderer,
    TemplateRenderError,
    render_code,
)

__all__ = [
    # Template loader
    "TemplateLoader",
    "TemplateLoadError",
    "TemplateValidationError",
    "load_template",
    "list_available_templates",
    "get_template_summary",
    # Template renderer
    "TemplateRenderer",
    "TemplateRenderError",
    "render_code",
]
