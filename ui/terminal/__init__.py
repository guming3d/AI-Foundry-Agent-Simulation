"""
Terminal UI (TUI) for Microsoft Foundry Agent Toolkit.

Built with Textual library for a rich terminal experience.
Includes theme support with multiple built-in themes.
Theme preferences are persisted locally.

Usage:
    from ui.terminal import run_tui
    run_tui()

Theme switching:
    Press 't' to open theme selector during runtime.
    Selected theme is automatically saved and restored on next launch.
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
from .preferences import get_preferences, UserPreferences

__all__ = [
    "AgentToolkitApp",
    "run_tui",
    "APP_THEMES",
    "THEME_NAMES",
    "DEFAULT_THEME",
    "register_app_themes",
    "get_theme_by_name",
    "get_next_theme",
    "get_preferences",
    "UserPreferences",
]
