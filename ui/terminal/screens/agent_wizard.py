"""
Agent creation wizard screen for the Textual TUI application.

Guides users through agent creation from industry profiles.
"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Button, Input, DataTable, ProgressBar, Label
from textual.containers import Container, Vertical, Horizontal
from textual import work

from ui.shared.state_manager import get_state_manager, get_state
from src.core.agent_manager import AgentManager
from src.core import config


class AgentWizardScreen(Screen):
    """Screen for creating agents from industry profiles."""

    BINDINGS = [
        ("escape", "app.pop_screen()", "Back"),
        ("c", "create_agents", "Create Agents"),
        ("r", "refresh_existing", "Refresh Existing"),
    ]

    def __init__(self):
        super().__init__()
        self.is_creating = False
        self.is_loading_existing = False
        self.existing_agents = []

    def compose(self) -> ComposeResult:
        yield Container(
            Static("Agent Creation Wizard", id="title", classes="screen-title"),

            # Existing Agents Section
            Vertical(
                Horizontal(
                    Static("Existing Agents in Azure:", classes="section-title"),
                    Button("Refresh [R]", id="btn-refresh-existing", variant="default", classes="small-button"),
                    classes="section-header-with-button",
                ),
                Static(id="existing-agents-summary", classes="info-text"),
                DataTable(id="existing-agents-table"),
                id="existing-agents-panel",
            ),

            Vertical(
                Static("Current Configuration:", classes="section-title"),
                Static(id="config-summary"),
                id="config-panel",
            ),
            Horizontal(
                Vertical(
                    Static("Organizations:", classes="label"),
                    Input(value="1", id="org-count", type="integer"),
                    id="org-input",
                ),
                Vertical(
                    Static("Agents per type:", classes="label"),
                    Input(value="1", id="agent-count", type="integer"),
                    id="agent-input",
                ),
                id="config-inputs",
            ),
            Static(id="total-agents", classes="info-text"),
            Horizontal(
                Button("Create Agents [C]", id="btn-create", variant="primary"),
                Button("Back", id="btn-back"),
                id="button-bar",
            ),
            Static("Tip: Use Daemon [D] for continuous production traffic simulation", classes="info-text"),
            Vertical(
                Static("Progress:", classes="section-title"),
                ProgressBar(id="progress-bar", total=100, show_eta=False),
                Static(id="progress-status"),
                id="progress-panel",
            ),
            Vertical(
                Static("Recently Created Agents:", classes="section-title"),
                DataTable(id="agents-table"),
                id="agents-panel",
            ),
            id="wizard-container",
        )

    def on_mount(self) -> None:
        """Initialize the screen."""
        # Setup created agents table
        table = self.query_one("#agents-table", DataTable)
        table.add_columns("Name", "Model", "Type", "Status")

        # Setup existing agents table
        existing_table = self.query_one("#existing-agents-table", DataTable)
        existing_table.add_columns("Name", "Azure ID", "Version", "Model")

        self._update_config_summary()
        self._update_total_agents()
        self._load_created_agents()
        self.action_refresh_existing()

    def on_screen_resume(self) -> None:
        """Update when returning to this screen."""
        self._update_config_summary()
        self._update_total_agents()
        self.action_refresh_existing()

    def _update_config_summary(self) -> None:
        """Update the configuration summary."""
        state = get_state()
        summary = self.query_one("#config-summary", Static)

        models = ", ".join(state.selected_models) if state.selected_models else "None selected"
        profile = state.current_profile.metadata.name if state.current_profile else "None selected"
        agent_types = len(state.current_profile.agent_types) if state.current_profile else 0

        summary.update(f"""
  Profile: {profile}
  Agent Types: {agent_types}
  Models: {models}
        """)

    def _update_total_agents(self) -> None:
        """Update the total agents count."""
        state = get_state()
        total_label = self.query_one("#total-agents", Static)

        try:
            org_count = int(self.query_one("#org-count", Input).value or "1")
            agent_count = int(self.query_one("#agent-count", Input).value or "1")
        except ValueError:
            org_count = 1
            agent_count = 1

        agent_types = len(state.current_profile.agent_types) if state.current_profile else 0
        total = org_count * agent_count * agent_types

        total_label.update(f"Total agents to create: {total}")

    def _load_created_agents(self) -> None:
        """Load recently created agents from state into the table."""
        state = get_state()
        table = self.query_one("#agents-table", DataTable)
        table.clear()

        for agent in state.created_agents:
            table.add_row(
                agent.name,
                agent.model,
                agent.agent_type or "Unknown",
                "Created"
            )

    def action_refresh_existing(self) -> None:
        """Refresh the existing agents list from Azure."""
        if self.is_loading_existing:
            self.notify("Already loading existing agents...", severity="warning")
            return

        self.refresh_existing_async()

    @work(thread=True)
    def refresh_existing_async(self) -> None:
        """Load existing agents from Azure in background thread."""
        self.is_loading_existing = True
        self.app.call_from_thread(self._update_existing_summary, "Loading...")

        try:
            manager = AgentManager()
            agents = manager.list_agents()
            self.existing_agents = agents

            self.app.call_from_thread(self._populate_existing_table, agents)
            self.app.call_from_thread(
                self._update_existing_summary,
                f"Found {len(agents)} existing agents in Azure AI Foundry project"
            )

        except Exception as e:
            self.app.call_from_thread(
                self._update_existing_summary,
                f"Error loading agents: {e}"
            )
            self.app.call_from_thread(self.notify, f"Error: {e}", severity="error")

        finally:
            self.is_loading_existing = False

    def _populate_existing_table(self, agents: list) -> None:
        """Populate the existing agents table."""
        table = self.query_one("#existing-agents-table", DataTable)
        table.clear()

        for agent in agents:
            table.add_row(
                agent.get("name", "Unknown"),
                agent.get("id", "N/A")[:20] + "..." if len(agent.get("id", "")) > 20 else agent.get("id", "N/A"),
                str(agent.get("version", "N/A")),
                agent.get("model", "N/A"),
            )

    def _update_existing_summary(self, message: str) -> None:
        """Update the existing agents summary."""
        summary = self.query_one("#existing-agents-summary", Static)
        summary.update(message)

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes."""
        self._update_total_agents()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "btn-create":
            self.action_create_agents()
        elif button_id == "btn-back":
            self.app.pop_screen()
        elif button_id == "btn-refresh-existing":
            self.action_refresh_existing()

    def action_create_agents(self) -> None:
        """Create agents based on current configuration."""
        state = get_state()

        if not state.current_profile:
            self.notify("Please select an industry profile first", severity="warning")
            return

        if not state.selected_models:
            self.notify("Please select at least one model", severity="warning")
            return

        if self.is_creating:
            self.notify("Agent creation already in progress", severity="warning")
            return

        try:
            org_count = int(self.query_one("#org-count", Input).value or "1")
            agent_count = int(self.query_one("#agent-count", Input).value or "1")
        except ValueError:
            self.notify("Invalid input values", severity="error")
            return

        self.is_creating = True
        progress = self.query_one("#progress-bar", ProgressBar)
        status = self.query_one("#progress-status", Static)

        total = org_count * agent_count * len(state.current_profile.agent_types)
        progress.update(total=total, progress=0)

        def progress_callback(current, total_count, message):
            progress.update(progress=current)
            status.update(message)

        try:
            manager = AgentManager(models=state.selected_models)
            result = manager.create_agents_from_profile(
                profile=state.current_profile,
                agent_count=agent_count,
                org_count=org_count,
                models=state.selected_models,
                progress_callback=progress_callback,
            )

            # Save to CSV using default path from config
            manager.save_agents_to_csv(result.created)
            csv_path = str(config.CREATED_AGENTS_CSV)

            # Update state
            get_state_manager().set_created_agents(result.created, csv_path)

            # Refresh tables
            self._load_created_agents()
            self.action_refresh_existing()

            status.update(f"Created {len(result.created)} agents, {len(result.failed)} failed")
            self.notify(f"Successfully created {len(result.created)} agents")

        except Exception as e:
            status.update(f"Error: {e}")
            self.notify(f"Error creating agents: {e}", severity="error")

        finally:
            self.is_creating = False
