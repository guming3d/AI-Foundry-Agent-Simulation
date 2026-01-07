"""
Tab components for the Gradio Web UI.
"""

from .model_tab import create_model_tab
from .profile_tab import create_profile_tab
from .agent_tab import create_agent_tab
from .simulation_tab import create_simulation_tab
from .results_tab import create_results_tab

__all__ = [
    "create_model_tab",
    "create_profile_tab",
    "create_agent_tab",
    "create_simulation_tab",
    "create_results_tab",
]
