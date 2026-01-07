"""
Home screen for the Textual TUI application.

Provides navigation and status overview.
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
           Agent Creation & Demo Toolkit
"""


class HomeScreen(Screen):
    """Home screen with navigation and status."""

    BINDINGS = [
        ("m", "app.push_screen('models')", "Models"),
        ("p", "app.push_screen('profiles')", "Profiles"),
        ("a", "app.push_screen('agents')", "Agents"),
        ("s", "app.push_screen('simulation')", "Simulate"),
        ("r", "app.push_screen('results')", "Results"),
    ]

    def compose(self) -> ComposeResult:
        yield Container(
            Static(LOGO, id="logo"),
            Static("Welcome to the Azure AI Foundry Agent Toolkit", id="welcome"),
            Vertical(
                Static("Quick Start Guide:", classes="section-title"),
                Static("1. Select models to use for your agents", classes="guide-step"),
                Static("2. Choose an industry profile or customize", classes="guide-step"),
                Static("3. Configure and create agents", classes="guide-step"),
                Static("4. Generate simulation code", classes="guide-step"),
                Static("5. Run simulations and view results", classes="guide-step"),
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
