"""
Terminal UI (TUI) for Azure AI Foundry Agent Toolkit.

Built with Textual library for a rich terminal experience.
Includes theme support with multiple built-in themes.

Usage:
    from ui.terminal import run_tui
    run_tui()

Theme switching:
    Press 't' to cycle through available themes during runtime.
"""

from .app import AgentToolkitApp, run_tui
from .themes import (
    APP_THEMES,
    THEME_NAMES,
    DEFAULT_THEME,
    register_app_themes,
    get_theme_by_name,
    get_next_theme,
)

__all__ = [
    "AgentToolkitApp",
    "run_tui",
    "APP_THEMES",
    "THEME_NAMES",
    "DEFAULT_THEME",
    "register_app_themes",
    "get_theme_by_name",
    "get_next_theme",
]
