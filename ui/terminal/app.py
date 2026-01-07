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
        Binding("q", "quit", "Quit", show=True),
        Binding("h", "push_screen('home')", "Home", show=True),
        Binding("m", "push_screen('models')", "Models", show=True),
        Binding("p", "push_screen('profiles')", "Profiles", show=True),
        Binding("a", "push_screen('agents')", "Agents", show=True),
        Binding("s", "push_screen('simulation')", "Simulate", show=True),
        Binding("r", "push_screen('results')", "Results", show=True),
        Binding("escape", "go_back", "Back", show=False),
    ]

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
        self.push_screen("home")

    def action_go_back(self) -> None:
        """Go back to previous screen or home."""
        if len(self.screen_stack) > 1:
            self.pop_screen()
        else:
            self.push_screen("home")


def run_tui():
    """Run the Textual TUI application."""
    app = AgentToolkitApp()
    app.run()


if __name__ == "__main__":
    run_tui()
