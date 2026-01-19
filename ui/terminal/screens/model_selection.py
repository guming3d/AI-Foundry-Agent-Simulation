"""
Model selection screen for the Textual TUI application.

Allows users to select models for agent deployment.
"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Button, DataTable, Checkbox, Label, Header, Footer
from textual.containers import Container, Vertical, Horizontal

from ui.shared.state_manager import get_state_manager
from src.core.model_manager import ModelManager


class ModelSelectionScreen(Screen):
    """Screen for selecting and managing models."""

    BINDINGS = [
        ("escape", "app.pop_screen()", "Back"),
        ("r", "refresh_models", "Refresh"),
        ("s", "save_selection", "Save"),
        ("space", "toggle_current", "Toggle"),
        ("enter", "toggle_current", "Toggle"),
    ]

    def __init__(self):
        super().__init__()
        self.model_manager = ModelManager()
        self.selected_models = set()

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static("Model Selection", id="title", classes="screen-title"),
            Static("Select models to use for your agents. These will be randomly assigned during agent creation.",
                   classes="description"),
            DataTable(id="model-table"),
            Horizontal(
                Button("Select All", id="btn-select-all"),
                Button("Clear All", id="btn-clear-all"),
                Button("Refresh [R]", id="btn-refresh"),
                Button("Save Selection [S]", id="btn-save", variant="primary"),
                Button("Back", id="btn-back", variant="default"),
                id="button-bar",
            ),
            Static(id="status-bar", classes="status-bar"),
            id="model-container",
        )
        yield Footer()

    def on_mount(self) -> None:
        """Initialize the model table."""
        table = self.query_one("#model-table", DataTable)
        table.cursor_type = "row"

        # Add columns if not already present
        if not table.columns:
            table.add_columns("Selected", "Model Name", "Capabilities", "Version")

        # Load current selection
        state = get_state_manager().state
        self.selected_models = set(state.selected_models)

        self._populate_table()

    def _populate_table(self) -> None:
        """Populate the model table."""
        table = self.query_one("#model-table", DataTable)

        # Clear existing rows only (not columns)
        table.clear(columns=False)

        models = self.model_manager.list_available_models()

        if not models:
            table.add_row("", "No models found", "Check Azure connection", "")
            self._update_status()
            return

        for model in models:
            is_selected = model.name in self.selected_models
            selected_mark = "[X]" if is_selected else "[ ]"
            capabilities = ", ".join(model.capabilities) if model.capabilities else "N/A"
            version = model.version or "N/A"
            table.add_row(selected_mark, model.name, capabilities, version, key=model.name)

        self._update_status()

    def _update_status(self) -> None:
        """Update the status bar."""
        status = self.query_one("#status-bar", Static)
        count = len(self.selected_models)
        status.update(f"Selected: {count} model(s)")

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Toggle model selection when row is clicked."""
        model_name = str(event.row_key.value)
        if model_name in self.selected_models:
            self.selected_models.discard(model_name)
        else:
            self.selected_models.add(model_name)
        self._populate_table()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "btn-select-all":
            models = self.model_manager.list_available_models()
            self.selected_models = {m.name for m in models}
            self._populate_table()

        elif button_id == "btn-clear-all":
            self.selected_models.clear()
            self._populate_table()

        elif button_id == "btn-refresh":
            self.action_refresh_models()

        elif button_id == "btn-save":
            self.action_save_selection()

        elif button_id == "btn-back":
            self.app.pop_screen()

    def action_toggle_current(self) -> None:
        """Toggle selection of the currently highlighted row."""
        table = self.query_one("#model-table", DataTable)
        try:
            # Get the cell key at current cursor position
            cell_key = table.coordinate_to_cell_key(table.cursor_coordinate)
            model_name = str(cell_key.row_key.value)
            if model_name:
                if model_name in self.selected_models:
                    self.selected_models.discard(model_name)
                    self.notify(f"Deselected: {model_name}")
                else:
                    self.selected_models.add(model_name)
                    self.notify(f"Selected: {model_name}")
                self._populate_table()
        except Exception:
            pass  # No valid row selected

    def action_refresh_models(self) -> None:
        """Refresh the model list."""
        self.model_manager.refresh_cache()
        self._populate_table()
        self.notify("Models refreshed")

    def action_save_selection(self) -> None:
        """Save the current selection."""
        if not self.selected_models:
            self.notify("Please select at least one model", severity="warning")
            return

        get_state_manager().set_selected_models(list(self.selected_models))
        self.notify(f"Saved {len(self.selected_models)} model(s)")
        self.app.pop_screen()
