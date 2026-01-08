"""
Industry profile screen for the Textual TUI application.

Allows users to browse, select, and customize industry profiles.
"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Button, DataTable, TextArea, Tree
from textual.containers import Container, Vertical, Horizontal

from ui.shared.state_manager import get_state_manager
from src.templates.template_loader import TemplateLoader


class IndustryProfileScreen(Screen):
    """Screen for managing industry profiles."""

    BINDINGS = [
        ("escape", "app.pop_screen()", "Back"),
        ("s", "select_profile", "Select"),
    ]

    def __init__(self):
        super().__init__()
        self.loader = TemplateLoader()
        self.current_profile_id = None

    def compose(self) -> ComposeResult:
        yield Container(
            Static("Industry Profiles", id="title", classes="screen-title"),
            Static("Select an industry profile to configure your agents.", classes="description"),
            Horizontal(
                Vertical(
                    Static("Available Profiles:", classes="section-title"),
                    DataTable(id="profile-table"),
                    id="profile-list",
                ),
                Vertical(
                    Static("Profile Details:", classes="section-title"),
                    Static(id="profile-details"),
                    id="profile-details-panel",
                ),
                id="main-content",
            ),
            Horizontal(
                Button("Select Profile [S]", id="btn-select", variant="primary"),
                Button("Back", id="btn-back"),
                id="button-bar",
            ),
            id="profile-container",
        )

    def on_mount(self) -> None:
        """Initialize the profile list."""
        table = self.query_one("#profile-table", DataTable)
        table.cursor_type = "row"

        # Add columns if not already present
        if not table.columns:
            table.add_columns("ID", "Name", "Agent Types")

        self._populate_table()

        # Show current selection
        state = get_state_manager().state
        if state.current_profile_id:
            self.current_profile_id = state.current_profile_id
            self._show_profile_details(state.current_profile_id)

    def _populate_table(self) -> None:
        """Populate the profile table."""
        table = self.query_one("#profile-table", DataTable)

        # Clear rows only, keep columns
        table.clear(columns=False)

        templates = self.loader.list_templates()

        if not templates:
            table.add_row("", "No profiles found", "", key="none")
            return

        for template_id in templates:
            try:
                info = self.loader.get_template_info(template_id)
                table.add_row(
                    info["id"],
                    info["name"],
                    str(info["agent_types"]),
                    key=template_id
                )
            except Exception as e:
                table.add_row(template_id, "Error loading", "-", key=template_id)

    def _show_profile_details(self, profile_id: str) -> None:
        """Show details for the selected profile."""
        details_panel = self.query_one("#profile-details", Static)

        try:
            profile = self.loader.load_template(profile_id)

            details = f"""
[b]Name:[/b] {profile.metadata.name}
[b]Version:[/b] {profile.metadata.version}
[b]Description:[/b] {profile.metadata.description or 'N/A'}

[b]Organization Prefix:[/b] {profile.organization.prefix}
[b]Departments:[/b] {len(profile.organization.departments)}

[b]Agent Types ({len(profile.agent_types)}):[/b]
"""
            for at in profile.agent_types:
                details += f"  - {at.name} ({at.id})\n"

            details += f"""
[b]Models:[/b]
  Preferred: {', '.join(profile.models.preferred) or 'None'}
  Allowed: {', '.join(profile.models.allowed) or 'None'}

[b]Guardrail Test Categories:[/b]
"""
            categories = profile.guardrail_tests.get_non_empty_categories()
            for cat, tests in categories.items():
                details += f"  - {cat}: {len(tests)} tests\n"

            details_panel.update(details)

        except Exception as e:
            details_panel.update(f"Error loading profile: {e}")

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Select profile when row is clicked or Enter pressed."""
        profile_id = str(event.row_key.value)
        if profile_id and profile_id != "none":
            self.current_profile_id = profile_id
            self._show_profile_details(profile_id)
            # Auto-select on row selection (double-click or Enter)
            self.action_select_profile()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Show profile details when cursor moves to a row."""
        if event.row_key:
            profile_id = str(event.row_key.value)
            if profile_id and profile_id != "none":
                self.current_profile_id = profile_id
                self._show_profile_details(profile_id)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "btn-select":
            self.action_select_profile()
        elif button_id == "btn-back":
            self.app.pop_screen()

    def action_select_profile(self) -> None:
        """Select the current profile."""
        if not self.current_profile_id:
            self.notify("Please select a profile first", severity="warning")
            return

        try:
            profile = self.loader.load_template(self.current_profile_id)
            get_state_manager().set_profile(profile, self.current_profile_id)
            self.notify(f"Selected profile: {profile.metadata.name}")
            self.app.pop_screen()
        except Exception as e:
            self.notify(f"Error selecting profile: {e}", severity="error")
