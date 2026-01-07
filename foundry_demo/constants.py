from __future__ import annotations

from pathlib import Path

APP_NAME = "AI Foundry Control Plane Demo"

MIN_SELECTED_MODELS = 5
MAX_SELECTED_MODELS = 8

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TEMPLATES_DIR = REPO_ROOT / "industry_templates"
DEFAULT_WORKSPACES_DIR = REPO_ROOT / "workspaces"

