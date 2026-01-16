"""
Home screen for the Textual TUI application.

Provides navigation, status overview, and quick start guide
for batch agent operations.
"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Button, Label
from textual.containers import Container, Vertical, Horizontal, Center
from textual import work

from ui.shared.state_manager import get_state, get_state_manager
from src.core.agent_manager import AgentManager
from .theme_select import ThemeSelectScreen
from ui.terminal.preferences import get_preferences


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
    ]

    def __init__(self):
        super().__init__()
        self.azure_agent_count = 0
        self.is_loading_agents = False

    def action_go_models(self) -> None:
        self.app.push_screen("models")

    def action_go_profiles(self) -> None:
        self.app.push_screen("profiles")

    def action_go_agents(self) -> None:
        self.app.push_screen("agents")

    def action_go_simulation(self) -> None:
        self.app.push_screen("simulation")

    def _get_workflow_status(self) -> dict:
        """Get the completion status of each workflow step."""
        state = get_state()

        return {
            "models": len(state.selected_models) > 0,
            "profiles": state.current_profile is not None,
            "agents": len(state.created_agents) > 0,
            "simulation": bool(state.operation_summary) or bool(state.guardrail_summary),
        }

    def _get_next_step(self) -> str:
        """Get the next incomplete workflow step."""
        status = self._get_workflow_status()

        steps = ["models", "profiles", "agents", "simulation"]
        for step in steps:
            if not status.get(step, False):
                return step

        return "simulation"

    def _format_step(self, step_num: int, name: str, key: str, completed: bool, is_next: bool) -> str:
        """Format a workflow step for display."""
        if completed:
            marker = "[X]"
            style = "green"
        elif is_next:
            marker = "[>]"
            style = "blue"
        else:
            marker = "[ ]"
            style = "dim"

        return f"{marker} {step_num}. {name} [{key}]"

    def compose(self) -> ComposeResult:
        yield Container(
            Static(LOGO, id="logo"),
            Static("Welcome to Azure AI Foundry Control-Plane Batch Agent Operation", id="welcome"),

            # Workflow Stepper
            Static("Workflow Progress:", classes="section-title"),
            Horizontal(
                Static(id="step-1"),
                Static(" -> ", classes="step-arrow"),
                Static(id="step-2"),
                Static(" -> ", classes="step-arrow"),
                Static(id="step-3"),
                Static(" -> ", classes="step-arrow"),
                Static(id="step-4"),
                id="workflow-stepper",
            ),

            # Navigation buttons - Main workflow
            Horizontal(
                Button("Models [M]", id="btn-models", variant="primary"),
                Button("Profiles [P]", id="btn-profiles", variant="primary"),
                Button("Agents [A]", id="btn-agents", variant="primary"),
                Button("Simulate [S]", id="btn-simulate", variant="primary"),
                id="nav-buttons",
            ),

            # Current Status - wrapped in bordered panel
            Vertical(
                Static("Current Status:", classes="section-title"),
                Static(id="status-models", classes="info-text"),
                Static(id="status-profile", classes="info-text"),
                Static(id="status-agents-azure", classes="info-text"),
                Static(id="status-agents-session", classes="info-text"),
                id="status-panel",
            ),

            # Settings row with theme button and exit
            Horizontal(
                Button("Theme", id="btn-theme", variant="default"),
                Button("Setup [C]", id="btn-setup", variant="default"),
                Button("Exit [Q]", id="btn-exit", variant="error"),
                id="nav-buttons-extra",
            ),

            id="home-container",
        )

    def on_mount(self) -> None:
        """Update status on mount."""
        self._update_status()
        self._update_stepper()
        self._load_azure_agent_count()

    def on_screen_resume(self) -> None:
        """Update status when returning to this screen."""
        self._update_status()
        self._update_stepper()
        self._load_azure_agent_count()

    def _update_stepper(self) -> None:
        """Update the workflow stepper display."""
        status = self._get_workflow_status()
        next_step = self._get_next_step()

        steps = [
            ("models", "Models", "M"),
            ("profiles", "Profile", "P"),
            ("agents", "Agents", "A"),
            ("simulation", "Simulate", "S"),
        ]

        for i, (step_id, name, key) in enumerate(steps, 1):
            completed = status.get(step_id, False)
            is_next = step_id == next_step and not completed

            widget = self.query_one(f"#step-{i}", Static)

            if completed:
                widget.update(f"[X]{i}.{name}")
                widget.remove_class("step-pending", "step-next")
                widget.add_class("step-completed")
            elif is_next:
                widget.update(f"[>]{i}.{name}")
                widget.remove_class("step-pending", "step-completed")
                widget.add_class("step-next")
            else:
                widget.update(f"[ ]{i}.{name}")
                widget.remove_class("step-completed", "step-next")
                widget.add_class("step-pending")

    def _update_status(self) -> None:
        """Update the status display."""
        state = get_state()

        models_status = self.query_one("#status-models", Static)
        models_count = len(state.selected_models)
        if models_count:
            models_status.update(f"  Models: {models_count} selected")
        else:
            models_status.update("  Models: None selected")

        profile_status = self.query_one("#status-profile", Static)
        if state.current_profile:
            profile_status.update(f"  Profile: {state.current_profile.metadata.name}")
        else:
            profile_status.update("  Profile: None selected")

        # Azure agents status
        azure_status = self.query_one("#status-agents-azure", Static)
        if self.is_loading_agents:
            azure_status.update("  Agents in Azure: Loading...")
        elif self.azure_agent_count > 0:
            azure_status.update(f"  Agents in Azure: {self.azure_agent_count} existing")
        else:
            azure_status.update("  Agents in Azure: 0 (no agents deployed)")

        # Session agents status
        session_status = self.query_one("#status-agents-session", Static)
        session_count = len(state.created_agents)
        if session_count:
            session_status.update(f"  Agents in Session: {session_count} created this session")
        else:
            session_status.update("  Agents in Session: None created")

    @work(thread=True)
    def _load_azure_agent_count(self) -> None:
        """Load the count of existing agents from Azure in background."""
        if self.is_loading_agents:
            return

        self.is_loading_agents = True
        self.app.call_from_thread(self._update_status)

        try:
            manager = AgentManager()
            agents = manager.list_agents()
            self.azure_agent_count = len(agents)
        except Exception:
            self.azure_agent_count = 0
        finally:
            self.is_loading_agents = False
            self.app.call_from_thread(self._update_status)

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
        elif button_id == "btn-theme":
            self._show_theme_selector()
        elif button_id == "btn-setup":
            self.app.push_screen("setup")
        elif button_id == "btn-exit":
            self.app.exit()

    def _show_theme_selector(self) -> None:
        """Show the theme selection dialog."""
        def handle_theme_selection(selected_theme: str | None) -> None:
            if selected_theme:
                self.app.theme = selected_theme
                # Save theme preference
                get_preferences().theme = selected_theme
                self.app.notify(f"Theme changed to: {selected_theme}", timeout=2)

        self.app.push_screen(
            ThemeSelectScreen(current_theme=self.app.theme),
            handle_theme_selection
        )
