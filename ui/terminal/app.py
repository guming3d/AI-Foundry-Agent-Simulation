"""
Main Textual TUI application for Azure AI Foundry Agent Toolkit.

Provides a rich terminal interface for:
- Model selection and deployment
- Industry profile management
- Agent generation
- Simulation execution
- Results visualization
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
from .screens.simulation import SimulationScreen
from .screens.results import ResultsScreen


class AgentToolkitApp(App):
    """
    Azure AI Foundry Agent Toolkit TUI Application.

    A terminal-based interface for creating, testing, and managing
    AI agents with Azure AI Foundry Control Plane.
    """

    TITLE = "Azure AI Foundry Agent Toolkit"
    SUB_TITLE = "Create, Test, and Monitor AI Agents"

    CSS_PATH = "styles/app.tcss"

    BINDINGS = [
        Binding("q", "request_quit", "Quit", show=True),
        Binding("ctrl+c", "request_quit", "Quit", show=False),
        Binding("ctrl+q", "request_quit", "Quit", show=False),
        Binding("h", "go_home", "Home", show=True),
        Binding("m", "go_models", "Models", show=True),
        Binding("p", "go_profiles", "Profiles", show=True),
        Binding("a", "go_agents", "Agents", show=True),
        Binding("s", "go_simulation", "Simulate", show=True),
        Binding("r", "go_results", "Results", show=True),
        Binding("escape", "go_back", "Back", show=False),
    ]

    # Use callable factories for screens (Textual 7.x compatible)
    SCREENS = {
        "home": HomeScreen,
        "models": ModelSelectionScreen,
        "profiles": IndustryProfileScreen,
        "agents": AgentWizardScreen,
        "simulation": SimulationScreen,
        "results": ResultsScreen,
    }

    def on_mount(self) -> None:
        """Called when the app is mounted."""
        # Use call_later to ensure app is fully running before pushing screen
        self.call_later(self._push_initial_screen)

    def _push_initial_screen(self) -> None:
        """Push the initial screen after app is fully running."""
        self.push_screen("home")

    def action_go_back(self) -> None:
        """Go back to previous screen or home."""
        if len(self.screen_stack) > 1:
            self.pop_screen()
        else:
            self.push_screen("home")

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

    def action_go_simulation(self) -> None:
        """Navigate to simulation screen."""
        self.push_screen("simulation")

    def action_go_results(self) -> None:
        """Navigate to results screen."""
        self.push_screen("results")

    def action_request_quit(self) -> None:
        """Handle quit request with cleanup."""
        # Stop any running simulation before quitting
        self._cleanup_simulations()
        self.exit()

    def _cleanup_simulations(self) -> None:
        """Stop any running simulations to allow clean exit."""
        # Find and stop any active simulation screens
        for screen in self.screen_stack:
            if isinstance(screen, SimulationScreen):
                if screen.engine and screen.simulation_active:
                    screen.engine.stop()
                    screen.simulation_active = False
                    screen.engine = None

    async def on_unmount(self) -> None:
        """Called when the app is being unmounted - cleanup."""
        self._cleanup_simulations()


def run_tui():
    """Run the Textual TUI application."""
    app = AgentToolkitApp()
    app.run()


if __name__ == "__main__":
    run_tui()
