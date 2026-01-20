"""
Main Textual TUI application for Microsoft Foundry Bootstrap.

Provides a rich terminal interface for:
- Batch agent creation (100+ agents)
- Model selection and deployment
- Industry profile management
- Parallel simulation execution
- Real-time metrics and visualization
"""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer, Static, Button, Label
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen

from .screens.home import HomeScreen
from .screens.model_selection import ModelSelectionScreen
from .screens.industry_profile import IndustryProfileScreen
from .screens.agent_wizard import AgentWizardScreen
from .screens.workflow_wizard import WorkflowWizardScreen
from .screens.simulation import SimulationScreen
from .screens.evaluation import EvaluationScreen
from .screens.daemon import DaemonScreen
from .screens.agent_management import AgentManagementScreen
from .screens.setup import SetupScreen
from .screens.theme_select import ThemeSelectScreen
from .themes import register_app_themes, get_next_theme, DEFAULT_THEME, THEME_NAMES
from .preferences import get_preferences

from src.core.env_validator import EnvValidator


class AgentToolkitApp(App):
    """
    Microsoft Foundry Bootstrap TUI Application.

    A terminal-based interface for batch creating, testing, and managing
    AI agents at scale with Microsoft Foundry Control Plane.
    """

    TITLE = "Microsoft Foundry Bootstrap"
    SUB_TITLE = "Batch Create, Test, and Monitor AI Agents at Scale"

    CSS_PATH = "styles/app.tcss"

    BINDINGS = [
        Binding("q", "request_quit", "Quit", show=True),
        Binding("ctrl+c", "request_quit", "Quit", show=False),
        Binding("ctrl+q", "request_quit", "Quit", show=False),
        Binding("t", "show_theme_selector", "Theme", show=True),
        Binding("h", "go_home", "Home", show=True),
        Binding("m", "go_models", "Models", show=True),
        Binding("p", "go_profiles", "Profiles", show=True),
        Binding("a", "go_agents", "Agents", show=True),
        Binding("w", "go_workflows", "Workflows", show=True),
        Binding("s", "go_simulation", "Simulate", show=True),
        Binding("e", "go_evaluations", "Eval", show=True),
        Binding("d", "go_daemon", "Daemon", show=True),
        Binding("x", "go_manage", "Manage", show=True),
        Binding("c", "go_setup", "Setup", show=True),
        Binding("escape", "go_back", "Back", show=False),
    ]

    # Use callable factories for screens (Textual 7.x compatible)
    SCREENS = {
        "home": HomeScreen,
        "models": ModelSelectionScreen,
        "profiles": IndustryProfileScreen,
        "agents": AgentWizardScreen,
        "workflows": WorkflowWizardScreen,
        "simulation": SimulationScreen,
        "evaluations": EvaluationScreen,
        "daemon": DaemonScreen,
        "agent_management": AgentManagementScreen,
        "setup": SetupScreen,
    }

    def on_mount(self) -> None:
        """Called when the app is mounted."""
        # Register custom themes
        register_app_themes(self)
        # Load saved theme preference or use default
        prefs = get_preferences()
        self.theme = prefs.theme
        # Use call_later to ensure app is fully running before pushing screen
        self.call_later(self._push_initial_screen)

    def notify(
        self,
        message: str,
        *,
        title: str | None = None,
        severity: str = "information",
        timeout: float = 3,
        markup: bool = False,
    ) -> None:
        """Send a notification with safe defaults for non-markup messages."""
        super().notify(
            message,
            title=title,
            severity=severity,
            timeout=timeout,
            markup=markup,
        )

    def _push_initial_screen(self) -> None:
        """Push the initial screen after app is fully running."""
        # Check if environment is configured
        if not EnvValidator.is_configured():
            self.push_screen("setup")
        else:
            self.push_screen("home")

    def action_go_back(self) -> None:
        """Go back to previous screen or home."""
        if len(self.screen_stack) > 1:
            self.pop_screen()
        else:
            self.push_screen("home")

    def action_cycle_theme(self) -> None:
        """Cycle through available themes."""
        current = self.theme
        next_theme = get_next_theme(current)
        self.theme = next_theme
        # Save theme preference
        get_preferences().theme = next_theme
        self.notify(f"Theme: {next_theme}", timeout=2)

    def action_show_theme_selector(self) -> None:
        """Show the theme selection dialog."""
        def handle_theme_selection(selected_theme: str | None) -> None:
            if selected_theme:
                self.theme = selected_theme
                # Save theme preference
                get_preferences().theme = selected_theme
                self.notify(f"Theme changed to: {selected_theme}", timeout=2)

        self.push_screen(
            ThemeSelectScreen(current_theme=self.theme),
            handle_theme_selection
        )

    def action_go_home(self) -> None:
        """Navigate to home screen."""
        self.push_screen("home")

    def action_go_models(self) -> None:
        """Navigate to models screen."""
        self.push_screen("models")

    def action_go_profiles(self) -> None:
        """Navigate to profiles screen."""
        self.push_screen("profiles")

    def action_go_agents(self) -> None:
        """Navigate to agents screen."""
        self.push_screen("agents")

    def action_go_workflows(self) -> None:
        """Navigate to workflows screen."""
        self.push_screen("workflows")

    def action_go_simulation(self) -> None:
        """Navigate to simulation screen."""
        self.push_screen("simulation")

    def action_go_evaluations(self) -> None:
        """Navigate to evaluations screen."""
        self.push_screen("evaluations")

    def action_go_daemon(self) -> None:
        """Navigate to daemon screen."""
        self.push_screen("daemon")

    def action_go_manage(self) -> None:
        """Navigate to agent management screen."""
        self.push_screen("agent_management")

    def action_go_setup(self) -> None:
        """Navigate to setup screen."""
        self.push_screen("setup")

    def action_request_quit(self) -> None:
        """Handle quit request with cleanup."""
        # Stop any running simulation before quitting
        self._cleanup_simulations()
        self.exit()

    def _cleanup_simulations(self) -> None:
        """Stop any running simulations and daemons to allow clean exit."""
        # Find and stop any active simulation screens
        for screen in self.screen_stack:
            if isinstance(screen, SimulationScreen):
                if screen.engine and screen.simulation_active:
                    screen.engine.stop()
                    screen.simulation_active = False
                    screen.engine = None
            elif isinstance(screen, DaemonScreen):
                if screen.daemon and screen.daemon.is_running:
                    screen.daemon.stop()

    async def on_unmount(self) -> None:
        """Called when the app is being unmounted - cleanup."""
        self._cleanup_simulations()


def run_tui():
    """Run the Textual TUI application."""
    app = AgentToolkitApp()
    app.run()


if __name__ == "__main__":
    run_tui()
