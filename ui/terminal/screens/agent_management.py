"""
Agent management screen for the Textual TUI application.

Allows users to view all agents in the Azure AI Foundry project
and delete them individually or in bulk.
"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Button, DataTable, ProgressBar
from textual.containers import Container, Vertical, Horizontal
from textual import work

from ui.shared.state_manager import get_state_manager, get_state
from src.core.agent_manager import AgentManager


class AgentManagementScreen(Screen):
    """Screen for managing agents in the Azure AI Foundry project."""

    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("r", "refresh_agents", "Refresh"),
        ("d", "delete_all", "Delete All"),
    ]

    DEFAULT_CSS = """
    AgentManagementScreen {
        layout: vertical;
    }

    #manage-header {
        height: auto;
        padding: 0 1;
    }

    #button-bar {
        height: auto;
        padding: 1;
        align: center middle;
    }

    #button-bar Button {
        margin: 0 1;
    }

    #agents-panel {
        height: 1fr;
        min-height: 15;
        padding: 0 1;
    }

    #agents-table {
        height: 1fr;
        border: solid $primary;
    }

    #progress-panel {
        height: auto;
        max-height: 4;
        padding: 0 1;
    }

    #status-panel {
        height: auto;
        padding: 0 1;
        margin-top: 1;
    }

    .warning-text {
        color: $warning;
        text-style: bold;
    }
    """

    def __init__(self):
        super().__init__()
        self.is_loading = False
        self.is_deleting = False
        self.delete_confirmed = False

    def action_go_back(self) -> None:
        """Go back to previous screen."""
        self.app.pop_screen()

    def compose(self) -> ComposeResult:
        yield Static("Manage Agents", id="title", classes="screen-title")
        yield Static("View and manage all agents in your Azure AI Foundry project", classes="description")

        yield Horizontal(
            Button("Refresh [R]", id="btn-refresh", variant="primary"),
            Button("Delete All [D]", id="btn-delete-all", variant="error"),
            Button("Back [Esc]", id="btn-back"),
            id="button-bar",
        )

        yield Vertical(
            Static("Agents in Project:", classes="section-title"),
            DataTable(id="agents-table"),
            id="agents-panel",
        )

        yield Vertical(
            ProgressBar(id="progress-bar", total=100, show_eta=False),
            Static("Ready", id="progress-status"),
            id="progress-panel",
        )

        yield Vertical(
            Static(id="status-message"),
            id="status-panel",
        )

    def on_mount(self) -> None:
        """Initialize the screen."""
        table = self.query_one("#agents-table", DataTable)
        table.add_columns("Name", "ID", "Version", "Model")
        self.action_refresh_agents()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "btn-refresh":
            self.action_refresh_agents()
        elif button_id == "btn-delete-all":
            self.action_delete_all()
        elif button_id == "btn-back":
            self.app.pop_screen()

    def action_refresh_agents(self) -> None:
        """Refresh the agents list from Azure."""
        if self.is_loading:
            self.notify("Already loading agents...", severity="warning")
            return

        self.refresh_agents_async()

    @work(thread=True)
    def refresh_agents_async(self) -> None:
        """Load agents in background thread."""
        self.is_loading = True
        self.app.call_from_thread(self._update_status, "Loading agents from Azure...")
        self.app.call_from_thread(self._update_progress, 0, 100, "Connecting to Azure...")

        try:
            manager = AgentManager()
            self.app.call_from_thread(self._update_progress, 30, 100, "Fetching agent list...")

            agents = manager.list_agents()

            self.app.call_from_thread(self._update_progress, 80, 100, "Updating table...")
            self.app.call_from_thread(self._populate_table, agents)
            self.app.call_from_thread(self._update_progress, 100, 100, f"Loaded {len(agents)} agents")
            self.app.call_from_thread(self._update_status, f"Found {len(agents)} agents in project")
            self.app.call_from_thread(self.notify, f"Loaded {len(agents)} agents")

        except Exception as e:
            self.app.call_from_thread(self._update_status, f"Error: {e}")
            self.app.call_from_thread(self._update_progress, 0, 100, "Error loading agents")
            self.app.call_from_thread(self.notify, f"Error: {e}", severity="error")

        finally:
            self.is_loading = False

    def _populate_table(self, agents: list) -> None:
        """Populate the agents table."""
        table = self.query_one("#agents-table", DataTable)
        table.clear()

        for agent in agents:
            table.add_row(
                agent.get("name", "Unknown"),
                agent.get("id", "N/A"),
                str(agent.get("version", "N/A")),
                agent.get("model", "N/A"),
            )

    def _update_status(self, message: str) -> None:
        """Update status message."""
        status = self.query_one("#status-message", Static)
        status.update(message)

    def _update_progress(self, current: int, total: int, message: str) -> None:
        """Update progress display."""
        progress = self.query_one("#progress-bar", ProgressBar)
        status = self.query_one("#progress-status", Static)

        progress.update(total=total, progress=current)
        status.update(message)

    def action_delete_all(self) -> None:
        """Delete all agents with confirmation."""
        if self.is_deleting:
            self.notify("Deletion already in progress...", severity="warning")
            return

        if not self.delete_confirmed:
            # First click - show confirmation
            self.delete_confirmed = True
            self._update_status("Are you sure? Click 'Delete All' again to confirm deletion of ALL agents.")
            self.notify("Click 'Delete All' again to confirm", severity="warning")

            # Reset confirmation after 5 seconds
            def reset_confirmation():
                import time
                time.sleep(5)
                self.delete_confirmed = False
                self.app.call_from_thread(self._update_status, "Deletion cancelled (timeout)")

            import threading
            threading.Thread(target=reset_confirmation, daemon=True).start()
            return

        # Second click - proceed with deletion
        self.delete_confirmed = False
        self.delete_all_agents_async()

    @work(thread=True)
    def delete_all_agents_async(self) -> None:
        """Delete all agents in background thread."""
        self.is_deleting = True
        self.app.call_from_thread(self._update_status, "Deleting all agents...")

        def progress_callback(current, total, message):
            self.app.call_from_thread(self._update_progress, current, total, message)

        try:
            manager = AgentManager()
            result = manager.delete_all_agents(progress_callback=progress_callback)

            deleted = result.get("deleted_count", 0)
            failed = result.get("failed_count", 0)
            total = result.get("total", 0)

            self.app.call_from_thread(
                self._update_status,
                f"Deleted {deleted}/{total} agents. Failed: {failed}"
            )
            self.app.call_from_thread(
                self._update_progress,
                100, 100,
                f"Completed: {deleted} deleted, {failed} failed"
            )

            # Clear the state's created agents list
            get_state_manager().set_created_agents([], "")

            # Refresh the table
            self.app.call_from_thread(self._populate_table, [])
            self.app.call_from_thread(self.notify, f"Deleted {deleted} agents")

        except Exception as e:
            self.app.call_from_thread(self._update_status, f"Error: {e}")
            self.app.call_from_thread(self.notify, f"Error: {e}", severity="error")

        finally:
            self.is_deleting = False
