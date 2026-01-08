"""
Home screen for the Textual TUI application.

Provides navigation, status overview, and quick start guide
for batch agent operations.
"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Button, Label
from textual.containers import Container, Vertical, Horizontal, Center

from ui.shared.state_manager import get_state


LOGO = """
    _    ___   _____                     _
   / \\  |_ _| |  ___|__  _   _ _ __   __| |_ __ _   _
  / _ \\  | |  | |_ / _ \\| | | | '_ \\ / _` | '__| | | |
 / ___ \\ | |  |  _| (_) | |_| | | | | (_| | |  | |_| |
/_/   \\_\\___| |_|  \\___/ \\__,_|_| |_|\\__,_|_|   \\__, |
                                                |___/
      Control-Plane Batch Agent Operation
"""


class HomeScreen(Screen):
    """Home screen with navigation and status."""

    BINDINGS = [
        ("m", "go_models", "Models"),
        ("p", "go_profiles", "Profiles"),
        ("a", "go_agents", "Agents"),
        ("s", "go_simulation", "Simulate"),
        ("r", "go_results", "Results"),
    ]

    def action_go_models(self) -> None:
        self.app.push_screen("models")

    def action_go_profiles(self) -> None:
        self.app.push_screen("profiles")

    def action_go_agents(self) -> None:
        self.app.push_screen("agents")

    def action_go_simulation(self) -> None:
        self.app.push_screen("simulation")

    def action_go_results(self) -> None:
        self.app.push_screen("results")

    def compose(self) -> ComposeResult:
        yield Container(
            Static(LOGO, id="logo"),
            Static("Welcome to Azure AI Foundry Control-Plane Batch Agent Operation", id="welcome"),
            Vertical(
                Static("Quick Start Guide:", classes="section-title"),
                Static("1. Select models to use for your agents", classes="guide-step"),
                Static("2. Choose an industry profile or customize", classes="guide-step"),
                Static("3. Batch create agents (100+ at scale)", classes="guide-step"),
                Static("4. Run parallel simulations with real-time metrics", classes="guide-step"),
                Static("5. View results and performance dashboards", classes="guide-step"),
                id="guide",
            ),
            Horizontal(
                Button("Models [M]", id="btn-models", variant="primary"),
                Button("Profiles [P]", id="btn-profiles", variant="primary"),
                Button("Agents [A]", id="btn-agents", variant="primary"),
                Button("Simulate [S]", id="btn-simulate", variant="primary"),
                Button("Results [R]", id="btn-results", variant="primary"),
                id="nav-buttons",
            ),
            Vertical(
                Static("Current Status:", classes="section-title"),
                Static(id="status-models"),
                Static(id="status-profile"),
                Static(id="status-agents"),
                id="status-panel",
            ),
            id="home-container",
        )

    def on_mount(self) -> None:
        """Update status on mount."""
        self._update_status()

    def on_screen_resume(self) -> None:
        """Update status when returning to this screen."""
        self._update_status()

    def _update_status(self) -> None:
        """Update the status display."""
        state = get_state()

        models_status = self.query_one("#status-models", Static)
        models_count = len(state.selected_models)
        models_status.update(f"  Models: {models_count} selected" if models_count else "  Models: None selected")

        profile_status = self.query_one("#status-profile", Static)
        if state.current_profile:
            profile_status.update(f"  Profile: {state.current_profile.metadata.name}")
        else:
            profile_status.update("  Profile: None selected")

        agents_status = self.query_one("#status-agents", Static)
        agents_count = len(state.created_agents)
        agents_status.update(f"  Agents: {agents_count} created" if agents_count else "  Agents: None created")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id
        if button_id == "btn-models":
            self.app.push_screen("models")
        elif button_id == "btn-profiles":
            self.app.push_screen("profiles")
        elif button_id == "btn-agents":
            self.app.push_screen("agents")
        elif button_id == "btn-simulate":
            self.app.push_screen("simulation")
        elif button_id == "btn-results":
            self.app.push_screen("results")
