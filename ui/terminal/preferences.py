"""
User preferences management for the TUI application.

Handles loading and saving user preferences to a local JSON file.
Preferences include theme selection and other UI settings.
"""

import json
from pathlib import Path
from typing import Any

from .themes import DEFAULT_THEME, THEME_NAMES


# Default preferences file location (in user's home directory)
PREFERENCES_DIR = Path.home() / ".config" / "azure-ai-foundry-toolkit"
PREFERENCES_FILE = PREFERENCES_DIR / "preferences.json"


class UserPreferences:
    """Manages user preferences with persistence to local JSON file."""

    _instance = None
    _preferences: dict = None

    def __new__(cls):
        """Singleton pattern to ensure single preferences instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._preferences = {}
        return cls._instance

    def __init__(self):
        """Initialize preferences, loading from file if exists."""
        if not self._preferences:
            self._load()

    def _load(self) -> None:
        """Load preferences from file."""
        try:
            if PREFERENCES_FILE.exists():
                with open(PREFERENCES_FILE, "r") as f:
                    self._preferences = json.load(f)
            else:
                self._preferences = self._get_defaults()
        except (json.JSONDecodeError, IOError) as e:
            # If file is corrupted or unreadable, use defaults
            self._preferences = self._get_defaults()

    def _save(self) -> None:
        """Save preferences to file."""
        try:
            # Ensure directory exists
            PREFERENCES_DIR.mkdir(parents=True, exist_ok=True)
            
            with open(PREFERENCES_FILE, "w") as f:
                json.dump(self._preferences, f, indent=2)
        except IOError:
            # Silently fail if we can't write (read-only filesystem, etc.)
            pass

    def _get_defaults(self) -> dict:
        """Get default preferences."""
        return {
            "theme": DEFAULT_THEME,
            "version": 1,  # For future migrations
        }

    @property
    def theme(self) -> str:
        """Get the saved theme preference."""
        theme = self._preferences.get("theme", DEFAULT_THEME)
        # Validate theme exists
        if theme not in THEME_NAMES:
            theme = DEFAULT_THEME
        return theme

    @theme.setter
    def theme(self, value: str) -> None:
        """Set and save the theme preference."""
        if value in THEME_NAMES:
            self._preferences["theme"] = value
            self._save()

    def get(self, key: str, default: Any = None) -> Any:
        """Get a preference value."""
        return self._preferences.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a preference value and save."""
        self._preferences[key] = value
        self._save()

    def reset(self) -> None:
        """Reset all preferences to defaults."""
        self._preferences = self._get_defaults()
        self._save()


# Singleton accessor function
_user_preferences: UserPreferences = None


def get_preferences() -> UserPreferences:
    """Get the singleton UserPreferences instance."""
    global _user_preferences
    if _user_preferences is None:
        _user_preferences = UserPreferences()
    return _user_preferences
