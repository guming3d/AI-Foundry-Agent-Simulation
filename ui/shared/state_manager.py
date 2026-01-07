"""
Shared state manager for Azure AI Foundry Agent Toolkit UI.

Provides centralized state management for both TUI and Web UI.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path

from src.models.industry_profile import IndustryProfile
from src.models.agent import CreatedAgent


@dataclass
class AppState:
    """Application state shared between UI components."""

    # Selected models
    selected_models: List[str] = field(default_factory=list)

    # Current industry profile
    current_profile: Optional[IndustryProfile] = None
    current_profile_id: Optional[str] = None

    # Agent configuration
    agent_count: int = 1
    org_count: int = 1

    # Created agents
    created_agents: List[CreatedAgent] = field(default_factory=list)
    agents_csv_path: str = "created_agents_results.csv"

    # Generated code paths
    generated_code_dir: Optional[str] = None

    # Simulation state
    is_simulating: bool = False
    simulation_progress: int = 0
    simulation_total: int = 0
    simulation_message: str = ""

    # Results
    operation_summary: Dict[str, Any] = field(default_factory=dict)
    guardrail_summary: Dict[str, Any] = field(default_factory=dict)

    # Azure connection
    is_connected: bool = False
    endpoint: str = ""


class StateManager:
    """
    Singleton state manager for the application.

    Provides methods to access and modify application state.
    """

    _instance: Optional["StateManager"] = None
    _state: AppState = None

    def __new__(cls) -> "StateManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._state = AppState()
        return cls._instance

    @property
    def state(self) -> AppState:
        """Get the current application state."""
        return self._state

    def reset(self) -> None:
        """Reset the state to defaults."""
        self._state = AppState()

    # Model management
    def set_selected_models(self, models: List[str]) -> None:
        self._state.selected_models = models

    def add_model(self, model: str) -> None:
        if model not in self._state.selected_models:
            self._state.selected_models.append(model)

    def remove_model(self, model: str) -> None:
        if model in self._state.selected_models:
            self._state.selected_models.remove(model)

    # Profile management
    def set_profile(self, profile: IndustryProfile, profile_id: str) -> None:
        self._state.current_profile = profile
        self._state.current_profile_id = profile_id

    def clear_profile(self) -> None:
        self._state.current_profile = None
        self._state.current_profile_id = None

    # Agent configuration
    def set_agent_config(self, agent_count: int, org_count: int) -> None:
        self._state.agent_count = agent_count
        self._state.org_count = org_count

    # Created agents
    def set_created_agents(self, agents: List[CreatedAgent], csv_path: str = None) -> None:
        self._state.created_agents = agents
        if csv_path:
            self._state.agents_csv_path = csv_path

    # Generated code
    def set_generated_code_dir(self, path: str) -> None:
        self._state.generated_code_dir = path

    # Simulation state
    def start_simulation(self, total: int) -> None:
        self._state.is_simulating = True
        self._state.simulation_progress = 0
        self._state.simulation_total = total
        self._state.simulation_message = "Starting..."

    def update_simulation_progress(self, progress: int, message: str) -> None:
        self._state.simulation_progress = progress
        self._state.simulation_message = message

    def stop_simulation(self) -> None:
        self._state.is_simulating = False

    # Results
    def set_operation_summary(self, summary: Dict[str, Any]) -> None:
        self._state.operation_summary = summary

    def set_guardrail_summary(self, summary: Dict[str, Any]) -> None:
        self._state.guardrail_summary = summary

    # Connection
    def set_connected(self, connected: bool, endpoint: str = "") -> None:
        self._state.is_connected = connected
        self._state.endpoint = endpoint


def get_state() -> AppState:
    """Get the current application state."""
    return StateManager().state


def get_state_manager() -> StateManager:
    """Get the state manager singleton."""
    return StateManager()
