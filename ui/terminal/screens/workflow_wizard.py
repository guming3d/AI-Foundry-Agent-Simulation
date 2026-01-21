"""
Workflow builder screen for the Textual TUI application.

Allows users to batch create multi-agent workflows based on industry profiles.
"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Button, Input, DataTable, ProgressBar
from textual.containers import VerticalScroll, Horizontal, Vertical
from textual import work

from ui.shared.state_manager import get_state_manager, get_state
from src.core.workflow_manager import WorkflowManager


class WorkflowWizardScreen(Screen):
    """Screen for creating workflows from industry profiles."""

    BINDINGS = [
        ("escape", "app.pop_screen()", "Back"),
        ("c", "create_workflows", "Create Workflows"),
        ("m", "choose_models", "Models"),
        ("p", "choose_profile", "Profile"),
        ("r", "refresh_templates", "Refresh Templates"),
        ("s", "select_all", "Select All"),
        ("u", "deselect_all", "Deselect All"),
    ]

    def __init__(self):
        super().__init__()
        self.is_creating = False
        self.is_loading_existing = False
        self.templates = []
        self.selected_template_ids = set()
        self.template_row_keys = {}
        self.existing_workflows = []

    def compose(self) -> ComposeResult:
        yield Static("Workflow Builder", id="title", classes="screen-title")

        yield Vertical(
            VerticalScroll(
                Vertical(
                    Horizontal(
                        Static("Existing Workflows", classes="section-title"),
                        Button("Refresh", id="btn-refresh-existing-workflows", variant="default"),
                        classes="section-header-with-button",
                    ),
                    Static(id="existing-workflows-summary", classes="info-text"),
                    DataTable(id="existing-workflows-table"),
                    id="existing-workflows-panel",
                ),
                Vertical(
                    Horizontal(
                        Static("Create New Workflows", classes="section-title"),
                        Button("Refresh Templates [R]", id="btn-refresh-templates", variant="default"),
                        classes="section-header-with-button",
                    ),
                    Static(id="templates-status", classes="info-text"),
                    DataTable(id="workflow-templates-table"),
                    Horizontal(
                        Button("Select All [S]", id="btn-select-all", variant="primary"),
                        Button("Deselect All [U]", id="btn-deselect-all", variant="primary"),
                        id="template-buttons",
                    ),
                    Static("Current Configuration:", classes="section-title"),
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
                            id="org-input",
                        ),
                        Vertical(
                            Static("Workflows per template:", classes="label"),
                            Input(value="1", id="workflow-count", type="integer"),
                            id="workflow-input",
                        ),
                        id="config-inputs",
                    ),
                    Static(id="total-workflows", classes="info-text"),
                    Horizontal(
                        Button("Create Workflows [C]", id="btn-create", variant="primary"),
                        id="button-bar",
                    ),
                    Static(
                        "Tip: Workflows are created as workflow agents and reference new prompt agents.",
                        classes="info-text",
                    ),
                    Static("Progress:", classes="section-title"),
                    ProgressBar(id="progress-bar", total=100, show_eta=False),
                    Static(id="progress-status", classes="info-text"),
                    Static("Recently Created Workflows:", classes="section-title"),
                    DataTable(id="workflows-table"),
                    id="create-workflows-panel",
                ),
                id="workflow-scroll",
            ),
            Horizontal(
                Button("Back", id="btn-back"),
                id="workflow-footer",
            ),
            id="workflow-container",
        )

    def on_mount(self) -> None:
        """Initialize the screen."""
        templates_table = self.query_one("#workflow-templates-table", DataTable)
        templates_table.add_columns("Sel", "Template", "Roles", "Description")
        templates_table.cursor_type = "row"

        existing_table = self.query_one("#existing-workflows-table", DataTable)
        existing_table.add_columns("Name", "Azure ID", "Version")

        workflows_table = self.query_one("#workflows-table", DataTable)
        workflows_table.add_columns("Name", "Template", "Org", "Version")

        self._update_config_summary()
        self._load_created_workflows()
        self.action_refresh_existing_workflows()
        self.action_refresh_templates()

    def on_screen_resume(self) -> None:
        """Update when returning to this screen."""
        self._update_config_summary()
        self.action_refresh_existing_workflows()
        self.action_refresh_templates()

    def _update_config_summary(self) -> None:
        """Update the configuration summary."""
        state = get_state()
        summary = self.query_one("#config-summary", Static)

        models = ", ".join(state.selected_models) if state.selected_models else "None selected (press M)"
        profile = state.current_profile.metadata.name if state.current_profile else "None selected (press P)"

        summary.update(f"""
  Profile: {profile}
  Models: {models}
        """)

    def _update_total_workflows(self) -> None:
        """Update total workflows display."""
        total_label = self.query_one("#total-workflows", Static)
        try:
            org_count = int(self.query_one("#org-count", Input).value or "1")
            workflow_count = int(self.query_one("#workflow-count", Input).value or "1")
        except ValueError:
            org_count = 1
            workflow_count = 1

        selected_count = len(self.selected_template_ids)
        total = org_count * workflow_count * selected_count
        if selected_count:
            total_label.update(
                f"Total workflows to create: {total} "
                f"({org_count} orgs × {workflow_count} per template × {selected_count} templates)"
            )
        else:
            total_label.update("Total workflows to create: 0 (select templates)")

    def _load_created_workflows(self) -> None:
        """Load recently created workflows from state."""
        state = get_state()
        table = self.query_one("#workflows-table", DataTable)
        table.clear()

        for workflow in state.created_workflows:
            table.add_row(
                workflow.name,
                workflow.template_name,
                workflow.org_id,
                str(workflow.version),
            )

    def action_refresh_existing_workflows(self) -> None:
        """Refresh existing workflows from Azure."""
        if self.is_loading_existing:
            self.notify("Already loading existing workflows...", severity="warning")
            return

        self.refresh_existing_workflows_async()

    @work(thread=True)
    def refresh_existing_workflows_async(self) -> None:
        """Load existing workflows from Azure in background thread."""
        self.is_loading_existing = True
        self.app.call_from_thread(self._update_existing_summary, "Loading...")

        try:
            manager = WorkflowManager()
            workflows = manager.list_workflows()
            self.existing_workflows = workflows

            self.app.call_from_thread(self._populate_existing_table, workflows)
            self.app.call_from_thread(
                self._update_existing_summary,
                f"Found {len(workflows)} existing workflows in Microsoft Foundry project"
            )

        except Exception as e:
            self.app.call_from_thread(
                self._update_existing_summary,
                f"Error loading workflows: {e}"
            )
            self.app.call_from_thread(self.notify, f"Error: {e}", severity="error")

        finally:
            self.is_loading_existing = False

    def _update_existing_summary(self, message: str) -> None:
        """Update the existing workflows summary text."""
        summary = self.query_one("#existing-workflows-summary", Static)
        summary.update(message)

    def _populate_existing_table(self, workflows: list) -> None:
        """Populate the existing workflows table."""
        table = self.query_one("#existing-workflows-table", DataTable)
        table.clear()

        for workflow in workflows:
            version = workflow.get("version")
            table.add_row(
                workflow.get("name", ""),
                workflow.get("id", ""),
                str(version) if version is not None else "Unknown",
            )

    def action_refresh_templates(self) -> None:
        """Refresh workflow templates."""
        state = get_state()
        status = self.query_one("#templates-status", Static)

        if not state.current_profile:
            self.templates = []
            self.selected_template_ids = set()
            self._populate_templates_table([])
            status.update("Select an industry profile (P) to view workflow templates.")
            self._update_total_workflows()
            return

        self.templates = WorkflowManager.build_templates(state.current_profile)
        self.selected_template_ids = {template.id for template in self.templates}
        self._populate_templates_table(self.templates)

        if not self.templates:
            status.update("No workflow templates available for this profile.")
        else:
            status.update(f"Loaded {len(self.templates)} templates for {state.current_profile.metadata.name}.")

        self._update_total_workflows()

    def _populate_templates_table(self, templates: list) -> None:
        """Populate the workflow templates table."""
        table = self.query_one("#workflow-templates-table", DataTable)
        table.clear()
        self.template_row_keys.clear()

        for template in templates:
            if template.roles:
                roles_display = " -> ".join(
                    role.agent_type.name for role in template.roles
                )
            else:
                roles_display = "Human input"
            is_selected = template.id in self.selected_template_ids
            row_key = table.add_row(
                "[X]" if is_selected else "[ ]",
                template.name,
                roles_display,
                template.description,
            )
            self.template_row_keys[template.id] = row_key

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection in the templates table."""
        table = event.data_table
        if table.id != "workflow-templates-table":
            return

        row_key = event.row_key
        row_data = table.get_row(row_key)
        template_name = row_data[1] if row_data and len(row_data) > 1 else None

        template_id = None
        for template in self.templates:
            if template.name == template_name:
                template_id = template.id
                break

        if template_id:
            if template_id in self.selected_template_ids:
                self.selected_template_ids.discard(template_id)
            else:
                self.selected_template_ids.add(template_id)

            self._populate_templates_table(self.templates)
            self._update_total_workflows()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes."""
        self._update_total_workflows()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id
        if button_id == "btn-refresh-existing-workflows":
            self.action_refresh_existing_workflows()
        elif button_id == "btn-refresh-templates":
            self.action_refresh_templates()
        elif button_id == "btn-profile":
            self.action_choose_profile()
        elif button_id == "btn-models":
            self.action_choose_models()
        elif button_id == "btn-select-all":
            self.action_select_all()
        elif button_id == "btn-deselect-all":
            self.action_deselect_all()
        elif button_id == "btn-create":
            self.action_create_workflows()
        elif button_id == "btn-back":
            self.app.pop_screen()

    def action_select_all(self) -> None:
        """Select all workflow templates."""
        if not self.templates:
            self.notify("No templates available", severity="warning")
            return

        self.selected_template_ids = {template.id for template in self.templates}
        self._populate_templates_table(self.templates)
        self._update_total_workflows()
        self.notify(f"Selected all {len(self.selected_template_ids)} templates")

    def action_deselect_all(self) -> None:
        """Deselect all workflow templates."""
        if not self.selected_template_ids:
            self.notify("No templates selected", severity="warning")
            return

        self.selected_template_ids.clear()
        self._populate_templates_table(self.templates)
        self._update_total_workflows()
        self.notify("Cleared template selection")

    def action_create_workflows(self) -> None:
        """Create workflows based on selected templates."""
        if self.is_creating:
            self.notify("Workflow creation already in progress...", severity="warning")
            return

        state = get_state()
        if not state.current_profile:
            self.notify("Select an industry profile (P) before creating workflows.", severity="error")
            return

        if not state.selected_models:
            self.notify("Select at least one model (M) before creating workflows.", severity="error")
            return

        if not self.selected_template_ids:
            self.notify("Select at least one workflow template.", severity="warning")
            return

        self.create_workflows_async()

    @work(thread=True)
    def create_workflows_async(self) -> None:
        """Create workflows in background thread."""
        self.is_creating = True
        status = self.query_one("#progress-status", Static)

        try:
            org_count = int(self.query_one("#org-count", Input).value or "1")
            workflow_count = int(self.query_one("#workflow-count", Input).value or "1")
        except ValueError:
            org_count = 1
            workflow_count = 1

        def progress_callback(current: int, total: int, message: str) -> None:
            self.app.call_from_thread(self._update_progress, current, total, message)

        try:
            manager = WorkflowManager(models=get_state().selected_models)
            result = manager.create_workflows_from_profile(
                profile=get_state().current_profile,
                template_ids=list(self.selected_template_ids),
                workflows_per_template=workflow_count,
                org_count=org_count,
                models=get_state().selected_models,
                progress_callback=progress_callback,
            )

            existing = list(get_state().created_workflows)
            get_state_manager().set_created_workflows(existing + result.created)
            self.app.call_from_thread(self._load_created_workflows)

            status.update(
                f"Created {len(result.created)} workflows, {len(result.failed)} failed"
            )
            self.app.call_from_thread(
                self.notify,
                f"Created {len(result.created)} workflow(s)",
            )

        except Exception as e:
            status.update(f"Error: {e}")
            self.app.call_from_thread(
                self.notify,
                f"Error creating workflows: {e}",
                severity="error",
            )

        finally:
            self.is_creating = False

    def action_choose_models(self) -> None:
        """Navigate to model selection."""
        self.app.push_screen("models")

    def action_choose_profile(self) -> None:
        """Navigate to profile selection."""
        self.app.push_screen("profiles")

    def _update_progress(self, current: int, total: int, message: str) -> None:
        """Update progress bar and status."""
        progress = self.query_one("#progress-bar", ProgressBar)
        status = self.query_one("#progress-status", Static)

        progress.update(total=total, progress=current)
        status.update(message)
