"""
Home screen for the Textual TUI application.

Provides navigation, status overview, and quick start guide
for batch agent operations.
"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Button
from textual.containers import Container, Vertical, Horizontal
from textual import work

from ui.shared.state_manager import get_state
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
      Microsoft Foundry Bootstrap
"""


class HomeScreen(Screen):
    """Home screen with navigation and status."""

    BINDINGS = [
        ("a", "go_agents", "Agents"),
        ("w", "go_workflows", "Workflows"),
        ("e", "go_evaluations", "Evaluations"),
        ("s", "go_simulation", "Simulate"),
    ]

    def __init__(self):
        super().__init__()
        self.azure_agent_count = 0
        self.is_loading_agents = False

    def action_go_agents(self) -> None:
        self.app.push_screen("agents")

    def action_go_workflows(self) -> None:
        self.app.push_screen("workflows")

    def action_go_simulation(self) -> None:
        self.app.push_screen("simulation")

    def action_go_evaluations(self) -> None:
        self.app.push_screen("evaluations")

    def compose(self) -> ComposeResult:
        yield Container(
            Static(LOGO, id="logo"),
            Static("Welcome to Microsoft Foundry Bootstrap", id="welcome"),

            # Navigation buttons
            Horizontal(
                Button("Agents [A]", id="btn-agents", variant="primary"),
                Button("Workflows [W]", id="btn-workflows", variant="primary"),
                Button("Evaluations [E]", id="btn-evaluations", variant="primary"),
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
                Static(id="status-workflows-session", classes="info-text"),
                Static(id="status-evaluations", classes="info-text"),
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
        self._load_azure_agent_count()

    def on_screen_resume(self) -> None:
        """Update status when returning to this screen."""
        self._update_status()
        self._load_azure_agent_count()

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

        workflows_status = self.query_one("#status-workflows-session", Static)
        workflows_count = len(state.created_workflows)
        if workflows_count:
            workflows_status.update(f"  Workflows in Session: {workflows_count} created this session")
        else:
            workflows_status.update("  Workflows in Session: None created")

        evaluations_status = self.query_one("#status-evaluations", Static)
        evaluation_count = len(state.evaluation_runs)
        if evaluation_count:
            evaluations_status.update(f"  Evaluations: {evaluation_count} run(s) this session")
        else:
            evaluations_status.update("  Evaluations: None run yet")

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
        if button_id == "btn-agents":
            self.app.push_screen("agents")
        elif button_id == "btn-workflows":
            self.app.push_screen("workflows")
        elif button_id == "btn-evaluations":
            self.app.push_screen("evaluations")
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
