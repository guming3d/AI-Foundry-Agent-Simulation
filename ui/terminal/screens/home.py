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

from src.core.agent_manager import AgentManager
from src.core.daemon_service import DaemonService
from src.core.model_manager import ModelManager
from src.core.workflow_manager import WorkflowManager
from src.core import config
from .theme_select import ThemeSelectScreen
from ui.terminal.preferences import get_preferences


LOGO = r"""
______  _______                                ____________     __________                   _________                   
___   |/  /__(_)__________________________________  __/_  /_    ___  ____/_________  ______________  /___________  __    
__  /|_/ /__  /_  ___/_  ___/  __ \_  ___/  __ \_  /_ _  __/    __  /_   _  __ \  / / /_  __ \  __  /__  ___/_  / / /    
_  /  / / _  / / /__ _  /   / /_/ /(__  )/ /_/ /  __/ / /_      _  __/   / /_/ / /_/ /_  / / / /_/ / _  /   _  /_/ /     
/_/  /_/  /_/  \___/ /_/    \____//____/ \____//_/    \__/      /_/      \____/\__,_/ /_/ /_/\__,_/  /_/    _\__, /      
                                                                                                            /____/       
________            _____       _____                                                                                    
___  __ )_____________  /_________  /_____________ ________                                                              
__  __  |  __ \  __ \  __/_  ___/  __/_  ___/  __ `/__  __ \                                                             
_  /_/ // /_/ / /_/ / /_ _(__  )/ /_ _  /   / /_/ /__  /_/ /                                                             
/_____/ \____/\____/\__/ /____/ \__/ /_/    \__,_/ _  .___/                                                              
                                                   /_/                                                                   
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
        self.workflow_count = 0
        self.deployed_models: list[str] = []
        self.is_loading_project_stats = False
        self.daemon_service = DaemonService()

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
            # Static("Welcome to Microsoft Foundry Bootstrap", id="welcome"),

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
                Static(id="status-workflows", classes="info-text"),
                Static(id="status-agents", classes="info-text"),
                Static(id="status-evaluations", classes="info-text"),
                Static(id="status-daemon", classes="info-text"),
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
        self._load_project_stats()

    def on_screen_resume(self) -> None:
        """Update status when returning to this screen."""
        self._update_status()
        self._load_project_stats()

    def _update_status(self) -> None:
        """Update the status display."""
        models_status = self.query_one("#status-models", Static)
        if self.is_loading_project_stats and not self.deployed_models:
            models_status.update("  Deployed Models: Loading...")
        elif self.deployed_models:
            models_status.update(
                f"  Deployed Models: {self._format_model_list(self.deployed_models)}"
            )
        else:
            models_status.update("  Deployed Models: None found")

        workflows_status = self.query_one("#status-workflows", Static)
        if self.is_loading_project_stats and self.workflow_count == 0:
            workflows_status.update("  Workflows: Loading...")
        else:
            workflows_status.update(f"  Workflows: {self.workflow_count} total")

        agents_status = self.query_one("#status-agents", Static)
        if self.is_loading_project_stats and self.azure_agent_count == 0:
            agents_status.update("  Agents: Loading...")
        else:
            agents_status.update(f"  Agents: {self.azure_agent_count} total")

        evaluations_status = self.query_one("#status-evaluations", Static)
        evaluations_status.update(
            f"  Evaluations: {self._count_evaluation_results()} total"
        )

        daemon_status = self.query_one("#status-daemon", Static)
        daemon_running = self.daemon_service.is_running()
        daemon_status.update(
            f"  Simulation Daemon: {'Running' if daemon_running else 'Stopped'}"
        )

    def _format_model_list(self, models: list[str], max_items: int = 4) -> str:
        """Format a model list for compact display."""
        display_models = models[:max_items]
        extra_count = len(models) - len(display_models)
        formatted = ", ".join(display_models) if display_models else "None found"
        if extra_count > 0:
            formatted = f"{formatted} (+{extra_count} more)"
        return formatted

    def _count_evaluation_results(self) -> int:
        """Count evaluation result files stored locally."""
        results_dir = config.EVALUATIONS_RESULTS_DIR
        try:
            if not results_dir.exists():
                return 0
            return sum(
                1
                for path in results_dir.iterdir()
                if path.is_file() and path.suffix == ".json"
            )
        except Exception:
            return 0

    @work(thread=True)
    def _load_project_stats(self) -> None:
        """Load the project stats (models, workflows, agents) in background."""
        if self.is_loading_project_stats:
            return

        self.is_loading_project_stats = True
        self.app.call_from_thread(self._update_status)

        try:
            try:
                model_manager = ModelManager()
                models = model_manager.list_available_models()
                self.deployed_models = [model.name for model in models]
            except Exception:
                self.deployed_models = []

            try:
                workflow_manager = WorkflowManager()
                workflows = workflow_manager.list_workflows()
                self.workflow_count = len(workflows)
            except Exception:
                self.workflow_count = 0

            try:
                manager = AgentManager()
                agents = manager.list_agents()
                self.azure_agent_count = len(agents)
            except Exception:
                self.azure_agent_count = 0
        except Exception:
            self.deployed_models = []
            self.workflow_count = 0
            self.azure_agent_count = 0
        finally:
            self.is_loading_project_stats = False
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
