"""
Agent creation wizard screen for the Textual TUI application.

Guides users through agent creation from industry profiles,
and allows managing existing agents.
"""

from pathlib import Path
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Button, Input, DataTable, ProgressBar
from textual.containers import Vertical, Horizontal, VerticalScroll
from textual import work
from rich.markup import escape

from ui.shared.state_manager import get_state_manager, get_state
from src.core.agent_manager import AgentManager
from src.core import config
from src.models.agent import CreatedAgent


class AgentWizardScreen(Screen):
    """Screen for creating agents from industry profiles."""

    DEFAULT_CSS = """
    AgentWizardScreen {
        layout: vertical;
    }

    #wizard-container {
        padding: 0 1;
        height: 1fr;
    }

    VerticalScroll {
        height: 1fr;
    }

    /* Existing agents section - compact */
    #existing-section {
        height: auto;
        margin: 0 0 1 0;
        padding: 1;
        border: solid $secondary-darken-1;
        background: $surface-darken-1;
    }

    #existing-agents-table {
        height: auto;
        min-height: 4;
        max-height: 10;
        margin: 0 0 1 0;
    }

    #existing-agents-summary {
        margin: 0 0 1 0;
    }

    /* Action buttons row */
    #action-buttons {
        height: auto;
        margin: 0;
        align: left middle;
    }

    #action-buttons Button {
        margin-right: 1;
        min-width: 14;
    }

    /* Configuration section */
    #config-section {
        height: auto;
        margin: 0 0 1 0;
        padding: 1;
        border: solid $primary-darken-2;
        background: $surface-darken-1;
    }

    #config-summary {
        margin: 0 0 1 0;
        padding: 0 1;
        border-left: solid $accent;
        background: $surface-darken-2;
    }

    /* Config row with inputs side by side */
    #config-row {
        height: auto;
        margin: 0 0 1 0;
    }

    #config-row Vertical {
        width: 1fr;
        margin-right: 2;
    }

    #config-row Input {
        width: 100%;
    }

    #total-agents {
        color: $accent;
        text-style: bold;
        padding: 0;
        margin: 0 0 1 0;
    }

    /* Create buttons */
    #create-buttons {
        height: auto;
        margin: 0 0 1 0;
        padding: 0 1;
        align: left middle;
    }

    #create-buttons Button {
        margin-right: 1;
    }

    /* Delete status */
    #delete-status {
        margin: 1 0 0 0;
        padding: 0 1;
        border-left: solid $warning;
        background: $surface-darken-2;
    }

    /* Progress section */
    #progress-section {
        height: auto;
        margin: 0 0 1 0;
        padding: 1;
        border: solid $success-darken-1;
        background: $surface-darken-1;
    }

    #progress-bar {
        margin: 0 0 1 0;
    }

    #progress-status {
        margin: 0;
    }

    /* Recently created section */
    #recent-section {
        height: auto;
        margin: 0;
        padding: 1;
        border: solid $success-darken-1;
        background: $surface-darken-1;
    }

    #agents-table {
        height: auto;
        min-height: 4;
        max-height: 8;
        margin: 0;
    }

    .section-header {
        text-style: bold;
        color: $primary;
        margin: 0 0 1 0;
    }

    .tip-text {
        color: $text-muted;
        text-style: italic;
        margin: 1 0 0 0;
    }
    """

    BINDINGS = [
        ("escape", "app.pop_screen()", "Back"),
        ("c", "create_agents", "Create Agents"),
        ("m", "choose_models", "Models"),
        ("p", "choose_profile", "Profile"),
        ("r", "refresh_existing", "Refresh Existing"),
        ("d", "delete_all_agents", "Delete All"),
        ("s", "select_all", "Select All"),
        ("u", "deselect_all", "Deselect All"),
        ("enter", "use_selected", "Use Selected"),
    ]

    def __init__(self):
        super().__init__()
        self.is_creating = False
        self.is_loading_existing = False
        self.is_deleting = False
        self.delete_confirmed = False
        self.existing_agents = []
        self.selected_agent_names = set()
        self.agent_row_keys = {}

    def compose(self) -> ComposeResult:
        yield Static("Agent Creation Wizard", id="title", classes="screen-title")

        yield VerticalScroll(
            # Existing Agents Section
            Vertical(
                Horizontal(
                    Static("Existing Agents in Azure", classes="section-header"),
                    Button("Refresh [R]", id="btn-refresh-existing", variant="default"),
                    classes="section-header-with-button",
                ),
                Static(id="existing-agents-summary", classes="info-text"),
                DataTable(id="existing-agents-table"),
                Horizontal(
                    Button("Select All", id="btn-select-all", variant="primary"),
                    Button("Deselect", id="btn-deselect-all", variant="default"),
                    Button("Use Selected", id="btn-use-selected", variant="success"),
                    Button("Delete Sel.", id="btn-delete-selected", variant="warning"),
                    Button("Delete All", id="btn-delete-all", variant="error"),
                    id="action-buttons",
                ),
                Static(id="delete-status", classes="info-text"),
                id="existing-section",
            ),

            # Configuration Section
            Vertical(
                Static("Create New Agents", classes="section-header"),
                Static(id="config-summary", classes="info-text"),
                Horizontal(
                    Button("Select Profile [P]", id="btn-profile", variant="default"),
                    Button("Select Models [M]", id="btn-models", variant="default"),
                    id="config-buttons",
                ),
                Horizontal(
                    Vertical(
                        Static("Organizations:", classes="label"),
                        Input(value="1", id="org-count", type="integer"),
                    ),
                    Vertical(
                        Static("Agents per type:", classes="label"),
                        Input(value="1", id="agent-count", type="integer"),
                    ),
                    id="config-row",
                ),
                Static(id="total-agents"),
                Static("Tip: Use Daemon mode for continuous production traffic simulation", classes="tip-text"),
                id="config-section",
            ),

            # Progress Section
            Vertical(
                Static("Progress", classes="section-header"),
                ProgressBar(id="progress-bar", total=100, show_eta=False),
                Static("Ready", id="progress-status", classes="info-text"),
                id="progress-section",
            ),

            # Recently Created Agents
            Vertical(
                Static("Recently Created Agents", classes="section-header"),
                DataTable(id="agents-table"),
                id="recent-section",
            ),

            id="wizard-container",
        )

        yield Horizontal(
            Button("Create Agents [C]", id="btn-create", variant="primary"),
            Button("Back", id="btn-back", variant="default"),
            id="create-buttons",
        )

    def on_mount(self) -> None:
        """Initialize the screen."""
        # Setup created agents table
        table = self.query_one("#agents-table", DataTable)
        table.add_columns("Name", "Model", "Type", "Status")

        # Setup existing agents table with cursor for selection
        existing_table = self.query_one("#existing-agents-table", DataTable)
        existing_table.add_columns("Sel", "Name", "Azure ID", "Version", "Model")
        existing_table.cursor_type = "row"

        self._update_config_summary()
        self._update_total_agents()
        self._load_created_agents()
        self._update_delete_status()
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

        models = ", ".join(state.selected_models) if state.selected_models else "None (press M)"
        profile = state.current_profile.metadata.name if state.current_profile else "None (press P)"

        # Get agent type names
        if state.current_profile and state.current_profile.agent_types:
            agent_type_names = [at.name for at in state.current_profile.agent_types]
            types_count = len(agent_type_names)
            agent_types_display = f"{types_count} types"
        else:
            agent_types_display = "None"

        summary.update(f"Profile: {profile} | Types: {agent_types_display} | Models: {models}")

    def _update_total_agents(self) -> None:
        """Update the total agents count with calculation breakdown."""
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

        if agent_types > 0:
            total_label.update(
                f"Total: {total} agents ({org_count} orgs x {agent_count} agents/type x {agent_types} types)"
            )
        else:
            total_label.update(f"Total: {total} (select a profile first)")

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
                f"Found {len(agents)} agents in Azure"
            )

        except Exception as e:
            self.app.call_from_thread(
                self._update_existing_summary,
                f"Error: {e}"
            )
            self.app.call_from_thread(self.notify, f"Error: {e}", severity="error")

        finally:
            self.is_loading_existing = False

    def _populate_existing_table(self, agents: list) -> None:
        """Populate the existing agents table."""
        table = self.query_one("#existing-agents-table", DataTable)
        table.clear()
        self.agent_row_keys.clear()

        for agent in agents:
            agent_name = agent.get("name", "Unknown")
            is_selected = agent_name in self.selected_agent_names

            row_key = table.add_row(
                "[X]" if is_selected else "[ ]",
                agent_name,
                agent.get("id", "N/A")[:16] + "..." if len(agent.get("id", "")) > 16 else agent.get("id", "N/A"),
                str(agent.get("version", "N/A")),
                agent.get("model", "N/A"),
            )

            self.agent_row_keys[agent_name] = row_key

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
        elif button_id == "btn-profile":
            self.action_choose_profile()
        elif button_id == "btn-models":
            self.action_choose_models()
        elif button_id == "btn-back":
            self.app.pop_screen()
        elif button_id == "btn-refresh-existing":
            self.action_refresh_existing()
        elif button_id == "btn-select-all":
            self.action_select_all()
        elif button_id == "btn-deselect-all":
            self.action_deselect_all()
        elif button_id == "btn-use-selected":
            self.action_use_selected()
        elif button_id == "btn-delete-selected":
            self.action_delete_selected()
        elif button_id == "btn-delete-all":
            self.action_delete_all_agents()

    def action_create_agents(self) -> None:
        """Create agents based on current configuration."""
        state = get_state()

        if not state.current_profile:
            self.notify("Select an industry profile (P) before creating agents", severity="warning")
            return

        if not state.selected_models:
            self.notify("Select at least one model (M) before creating agents", severity="warning")
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

    def action_choose_models(self) -> None:
        """Navigate to model selection."""
        self.app.push_screen("models")

    def action_choose_profile(self) -> None:
        """Navigate to profile selection."""
        self.app.push_screen("profiles")

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection in the existing agents table."""
        table = event.data_table
        if table.id != "existing-agents-table":
            return

        # Get the agent name from the selected row
        row_key = event.row_key
        row_data = table.get_row(row_key)
        agent_name = row_data[1] if row_data and len(row_data) > 1 else None

        if agent_name:
            # Toggle selection
            if agent_name in self.selected_agent_names:
                self.selected_agent_names.discard(agent_name)
            else:
                self.selected_agent_names.add(agent_name)

            # Refresh the table to update all checkbox indicators
            self._populate_existing_table(self.existing_agents)
            self._update_delete_status()

    def _update_delete_status(self) -> None:
        """Update the delete status display."""
        count = len(self.selected_agent_names)
        if count == 0:
            self._update_delete_status_text("Click rows to select agents for simulation or deletion")
        else:
            self._update_delete_status_text(f"Selected {count} agent(s)")

    def action_select_all(self) -> None:
        """Select all agents in the table."""
        if not self.existing_agents:
            self.notify("No agents to select", severity="warning")
            return

        for agent in self.existing_agents:
            agent_name = agent.get("name", "Unknown")
            self.selected_agent_names.add(agent_name)

        self._populate_existing_table(self.existing_agents)
        self._update_delete_status()
        self.notify(f"Selected all {len(self.selected_agent_names)} agent(s)")

    def action_deselect_all(self) -> None:
        """Deselect all agents."""
        if not self.selected_agent_names:
            self.notify("No agents are selected", severity="warning")
            return

        count = len(self.selected_agent_names)
        self.selected_agent_names.clear()
        self._populate_existing_table(self.existing_agents)
        self._update_delete_status()
        self.notify(f"Deselected all {count} agent(s)")

    def action_use_selected(self) -> None:
        """Export selected agents to CSV for simulation without creating new ones."""
        if not self.selected_agent_names:
            self.notify("No agents selected. Please select agents first.", severity="warning")
            return

        self.use_selected_async()

    @work(thread=True)
    def use_selected_async(self) -> None:
        """Export selected agents to CSV in background thread."""
        selected_count = len(self.selected_agent_names)

        self.app.call_from_thread(
            self._update_delete_status_text,
            f"Exporting {selected_count} agent(s) to CSV..."
        )

        try:
            # Filter existing agents to only include selected ones
            selected_agents_data = [
                agent for agent in self.existing_agents
                if agent.get("name") in self.selected_agent_names
            ]

            # Convert to CreatedAgent objects
            created_agents = []
            for agent_data in selected_agents_data:
                name_parts = agent_data.get("name", "").split("-")
                org_id = name_parts[0] if len(name_parts) > 0 else "UNKNOWN"
                agent_id = name_parts[-1] if len(name_parts) > 2 else "AG001"

                created_agent = CreatedAgent(
                    agent_id=agent_id,
                    name=agent_data.get("name", "Unknown"),
                    azure_id=agent_data.get("id", ""),
                    version=agent_data.get("version") or "1",
                    model=agent_data.get("model") or "Unknown",
                    org_id=org_id,
                    agent_type=name_parts[1] if len(name_parts) > 1 else "Unknown"
                )
                created_agents.append(created_agent)

            # Save to CSV using AgentManager
            manager = AgentManager()
            config.ensure_directories()
            csv_path = str(config.CREATED_AGENTS_CSV)
            manager.save_agents_to_csv(created_agents, csv_path)

            # Update state
            self.app.call_from_thread(
                get_state_manager().set_created_agents,
                created_agents,
                csv_path
            )

            # Update the recently created table
            self.app.call_from_thread(self._load_created_agents)

            self.app.call_from_thread(
                self._update_delete_status_text,
                f"Exported {selected_count} agent(s) for simulation"
            )
            self.app.call_from_thread(
                self.notify,
                f"Ready for simulation with {selected_count} agent(s)!"
            )

        except Exception as e:
            self.app.call_from_thread(
                self._update_delete_status_text,
                f"Error: {e}"
            )
            self.app.call_from_thread(
                self.notify,
                f"Error: {e}",
                severity="error"
            )

    def action_delete_selected(self) -> None:
        """Delete selected agents."""
        if self.is_deleting:
            self.notify("Deletion already in progress", severity="warning")
            return

        if not self.selected_agent_names:
            self.notify("No agents selected. Click on rows to select agents.", severity="warning")
            return

        self.delete_selected_async()

    @work(thread=True)
    def delete_selected_async(self) -> None:
        """Delete selected agents in background thread."""
        self.is_deleting = True
        agents_to_delete = list(self.selected_agent_names)
        total = len(agents_to_delete)

        self.app.call_from_thread(
            self._update_delete_status_text,
            f"Deleting {total} agent(s)..."
        )

        manager = AgentManager()
        deleted = 0
        failed = 0

        for i, agent_name in enumerate(agents_to_delete):
            self.app.call_from_thread(
                self._update_delete_status_text,
                f"Deleting {agent_name} ({i+1}/{total})..."
            )

            if manager.delete_agent(agent_name):
                deleted += 1
            else:
                failed += 1

        # Clear selection
        self.selected_agent_names.clear()

        self.app.call_from_thread(
            self._update_delete_status_text,
            f"Deleted {deleted} agent(s), {failed} failed"
        )
        self.app.call_from_thread(self.notify, f"Deleted {deleted} agent(s)")
        self.app.call_from_thread(self.action_refresh_existing)

        self.is_deleting = False

    def _update_delete_status_text(self, message: str) -> None:
        """Update delete status text."""
        status = self.query_one("#delete-status", Static)
        status.update(escape(message))

    def action_delete_all_agents(self) -> None:
        """Delete all agents with confirmation."""
        if self.is_deleting:
            self.notify("Deletion already in progress", severity="warning")
            return

        if not self.existing_agents:
            self.notify("No agents to delete", severity="warning")
            return

        if not self.delete_confirmed:
            # First click - show confirmation
            self.delete_confirmed = True
            self._update_delete_status_text(
                f"Click 'Delete All' again to confirm deletion of {len(self.existing_agents)} agents"
            )
            self.notify("Click 'Delete All' again to confirm", severity="warning")

            # Reset confirmation after 5 seconds
            def reset_confirmation():
                import time
                time.sleep(5)
                self.delete_confirmed = False
                self.app.call_from_thread(
                    self._update_delete_status_text,
                    "Deletion cancelled (timeout)"
                )

            import threading
            threading.Thread(target=reset_confirmation, daemon=True).start()
            return

        # Second click - proceed with deletion
        self.delete_confirmed = False
        self.delete_all_async()

    @work(thread=True)
    def delete_all_async(self) -> None:
        """Delete all agents in background thread."""
        self.is_deleting = True
        self.app.call_from_thread(
            self._update_delete_status_text,
            "Deleting all agents..."
        )

        def progress_callback(current, total, message):
            self.app.call_from_thread(
                self._update_delete_status_text,
                f"{message} ({current}/{total})"
            )

        try:
            manager = AgentManager()
            result = manager.delete_all_agents(progress_callback=progress_callback)

            deleted = result.get("deleted_count", 0)
            failed = result.get("failed_count", 0)

            # Clear the state's created agents list
            get_state_manager().set_created_agents([], "")
            self.selected_agent_names.clear()

            self.app.call_from_thread(
                self._update_delete_status_text,
                f"Deleted {deleted} agent(s), {failed} failed"
            )
            self.app.call_from_thread(self.notify, f"Deleted {deleted} agents")
            self.app.call_from_thread(self.action_refresh_existing)
            self.app.call_from_thread(self._load_created_agents)

        except Exception as e:
            self.app.call_from_thread(
                self._update_delete_status_text,
                f"Error: {e}"
            )
            self.app.call_from_thread(self.notify, f"Error: {e}", severity="error")

        finally:
            self.is_deleting = False
