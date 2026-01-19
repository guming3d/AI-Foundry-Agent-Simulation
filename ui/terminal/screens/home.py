"""
Home screen for the Textual TUI application.

Provides navigation, status overview, and quick start guide
for batch agent operations.
"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Button
from textual.containers import Container, Vertical, Horizontal, Grid
from textual import work

from ui.shared.state_manager import get_state
from src.core.agent_manager import AgentManager
from .theme_select import ThemeSelectScreen
from ui.terminal.preferences import get_preferences


# Compact ASCII logo
LOGO = """
 ╔═══════════════════════════════════════════════════════════╗
 ║     █████╗ ██╗    ███████╗ ██████╗ ██╗   ██╗███╗   ██╗    ║
 ║    ██╔══██╗██║    ██╔════╝██╔═══██╗██║   ██║████╗  ██║    ║
 ║    ███████║██║    █████╗  ██║   ██║██║   ██║██╔██╗ ██║    ║
 ║    ██╔══██║██║    ██╔══╝  ██║   ██║██║   ██║██║╚██╗██║    ║
 ║    ██║  ██║██║    ██║     ╚██████╔╝╚██████╔╝██║ ╚████║    ║
 ║    ╚═╝  ╚═╝╚═╝    ╚═╝      ╚═════╝  ╚═════╝ ╚═╝  ╚═══╝    ║
 ║           Control-Plane  Batch Agent Operation            ║
 ╚═══════════════════════════════════════════════════════════╝"""


class HomeScreen(Screen):
    """Home screen with navigation and status."""

    DEFAULT_CSS = """
    HomeScreen {
        layout: vertical;
    }

    #home-container {
        padding: 0 2;
        align: center top;
    }

    #logo {
        text-align: center;
        color: $primary;
        padding: 0;
        margin: 0;
    }

    #nav-buttons {
        margin: 1 0;
        height: auto;
        align: center middle;
    }

    #nav-buttons Button {
        margin: 0 1;
        min-width: 16;
    }

    /* Status Grid - Dashboard style */
    #status-grid {
        grid-size: 3 2;
        grid-columns: 1fr 1fr 1fr;
        grid-rows: auto auto;
        grid-gutter: 1;
        margin: 0 0 1 0;
        padding: 0 4;
        height: auto;
    }

    .status-card {
        padding: 1;
        border: round $primary-darken-2;
        background: $surface;
        height: auto;
        min-height: 4;
    }

    .status-card-header {
        color: $text-muted;
        text-style: bold;
        margin-bottom: 0;
    }

    .status-card-value {
        color: $accent;
        text-style: bold;
    }

    .status-card-value.text-success {
        color: $success;
    }

    .status-card-value.text-warning {
        color: $warning;
    }

    /* Bottom buttons */
    #nav-buttons-extra {
        margin: 0;
        height: auto;
        align: center middle;
    }

    #nav-buttons-extra Button {
        margin: 0 1;
    }
    """

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

            # Navigation buttons
            Horizontal(
                Button("Agents [A]", id="btn-agents", variant="primary"),
                Button("Workflows [W]", id="btn-workflows", variant="primary"),
                Button("Evaluations [E]", id="btn-evaluations", variant="primary"),
                Button("Simulate [S]", id="btn-simulate", variant="success"),
                id="nav-buttons",
            ),

            # Status Dashboard Grid
            Grid(
                Vertical(
                    Static("Models Selected", classes="status-card-header"),
                    Static("0", id="status-models-value", classes="status-card-value"),
                    classes="status-card",
                ),
                Vertical(
                    Static("Industry Profile", classes="status-card-header"),
                    Static("None", id="status-profile-value", classes="status-card-value"),
                    classes="status-card",
                ),
                Vertical(
                    Static("Agents in Azure", classes="status-card-header"),
                    Static("Loading...", id="status-azure-value", classes="status-card-value"),
                    classes="status-card",
                ),
                Vertical(
                    Static("Session Agents", classes="status-card-header"),
                    Static("0", id="status-session-agents-value", classes="status-card-value"),
                    classes="status-card",
                ),
                Vertical(
                    Static("Session Workflows", classes="status-card-header"),
                    Static("0", id="status-session-workflows-value", classes="status-card-value"),
                    classes="status-card",
                ),
                Vertical(
                    Static("Evaluations Run", classes="status-card-header"),
                    Static("0", id="status-evaluations-value", classes="status-card-value"),
                    classes="status-card",
                ),
                id="status-grid",
            ),

            # Settings row with theme button and exit
            Horizontal(
                Button("Theme [T]", id="btn-theme", variant="default"),
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

        # Models
        models_value = self.query_one("#status-models-value", Static)
        models_count = len(state.selected_models)
        models_value.update(str(models_count) if models_count else "None")
        if models_count:
            models_value.remove_class("text-warning")
            models_value.add_class("text-success")
        else:
            models_value.remove_class("text-success")
            models_value.add_class("text-warning")

        # Profile
        profile_value = self.query_one("#status-profile-value", Static)
        if state.current_profile:
            profile_value.update(state.current_profile.metadata.name)
            profile_value.remove_class("text-warning")
            profile_value.add_class("text-success")
        else:
            profile_value.update("None")
            profile_value.remove_class("text-success")
            profile_value.add_class("text-warning")

        # Azure agents
        azure_value = self.query_one("#status-azure-value", Static)
        if self.is_loading_agents:
            azure_value.update("Loading...")
        else:
            azure_value.update(str(self.azure_agent_count))

        # Session agents
        session_agents_value = self.query_one("#status-session-agents-value", Static)
        session_count = len(state.created_agents)
        session_agents_value.update(str(session_count))

        # Session workflows
        workflows_value = self.query_one("#status-session-workflows-value", Static)
        workflows_count = len(state.created_workflows)
        workflows_value.update(str(workflows_count))

        # Evaluations
        evaluations_value = self.query_one("#status-evaluations-value", Static)
        evaluation_count = len(state.evaluation_runs)
        evaluations_value.update(str(evaluation_count))

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
