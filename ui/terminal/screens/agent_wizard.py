"""
Agent creation wizard screen for the Textual TUI application.

Guides users through agent creation and code generation.
"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Button, Input, DataTable, ProgressBar, Label
from textual.containers import Container, Vertical, Horizontal

from ui.shared.state_manager import get_state_manager, get_state
from src.core.agent_manager import AgentManager
from src.codegen.generator import generate_code_for_profile


class AgentWizardScreen(Screen):
    """Screen for creating agents and generating code."""

    BINDINGS = [
        ("escape", "app.pop_screen()", "Back"),
        ("g", "generate_code", "Generate Code"),
        ("c", "create_agents", "Create Agents"),
    ]

    def __init__(self):
        super().__init__()
        self.is_creating = False

    def compose(self) -> ComposeResult:
        yield Container(
            Static("Agent Creation Wizard", id="title", classes="screen-title"),
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
                Button("Generate Code [G]", id="btn-generate", variant="success"),
                Button("Back", id="btn-back"),
                id="button-bar",
            ),
            Vertical(
                Static("Progress:", classes="section-title"),
                ProgressBar(id="progress-bar", total=100, show_eta=False),
                Static(id="progress-status"),
                id="progress-panel",
            ),
            Vertical(
                Static("Created Agents:", classes="section-title"),
                DataTable(id="agents-table"),
                id="agents-panel",
            ),
            id="wizard-container",
        )

    def on_mount(self) -> None:
        """Initialize the screen."""
        # Setup agents table
        table = self.query_one("#agents-table", DataTable)
        table.add_columns("Name", "Model", "Type", "Status")

        self._update_config_summary()
        self._update_total_agents()
        self._load_existing_agents()

    def on_screen_resume(self) -> None:
        """Update when returning to this screen."""
        self._update_config_summary()
        self._update_total_agents()

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

    def _load_existing_agents(self) -> None:
        """Load existing agents into the table."""
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

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes."""
        self._update_total_agents()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "btn-create":
            self.action_create_agents()
        elif button_id == "btn-generate":
            self.action_generate_code()
        elif button_id == "btn-back":
            self.app.pop_screen()

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

            # Save to CSV
            csv_path = "created_agents_results.csv"
            manager.save_agents_to_csv(result.created, csv_path)

            # Update state
            get_state_manager().set_created_agents(result.created, csv_path)

            # Refresh table
            self._load_existing_agents()

            status.update(f"Created {len(result.created)} agents, {len(result.failed)} failed")
            self.notify(f"Successfully created {len(result.created)} agents")

        except Exception as e:
            status.update(f"Error: {e}")
            self.notify(f"Error creating agents: {e}", severity="error")

        finally:
            self.is_creating = False

    def action_generate_code(self) -> None:
        """Generate simulation code for the current profile."""
        state = get_state()

        if not state.current_profile:
            self.notify("Please select an industry profile first", severity="warning")
            return

        status = self.query_one("#progress-status", Static)
        status.update("Generating code...")

        try:
            output_dir = "output/generated_code"
            result = generate_code_for_profile(
                profile=state.current_profile,
                output_dir=output_dir,
                agents_csv=state.agents_csv_path,
            )

            get_state_manager().set_generated_code_dir(output_dir)

            files = "\n".join(f"  - {name}" for name in result.keys())
            status.update(f"Generated files:\n{files}")
            self.notify(f"Generated {len(result)} files to {output_dir}")

        except Exception as e:
            status.update(f"Error: {e}")
            self.notify(f"Error generating code: {e}", severity="error")
