"""
Evaluation screen for running sample evaluations against agents.
"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Button, DataTable, ProgressBar, Log, Select
from textual.containers import Horizontal, VerticalScroll, Vertical
from textual import work

from ui.shared.state_manager import get_state_manager
from src.core.agent_manager import AgentManager
from src.core.evaluation_engine import EvaluationEngine
from src.core.evaluation_templates import EvaluationTemplateLoader
from src.core.model_manager import ModelManager


class EvaluationScreen(Screen):
    """Screen for running sample evaluations."""

    BINDINGS = [
        ("escape", "app.pop_screen()", "Back"),
        ("r", "refresh_agents", "Refresh Agents"),
        ("enter", "run_evaluations", "Run"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.template_loader = EvaluationTemplateLoader()
        self.model_manager = ModelManager()
        self.templates = []
        self.selected_template_ids = set()
        self.selected_agent_names = set()
        self.template_row_keys = {}
        self.agent_row_keys = {}
        self.is_loading_agents = False
        self.is_loading_models = False
        self.is_loading_evaluations = False
        self.evaluation_running = False
        self.agents = []
        self.models = []

    def compose(self) -> ComposeResult:
        yield Static("Sample Evaluations", id="title", classes="screen-title")
        yield Static(
            "Select evaluation templates and agents, then run evaluations.",
            classes="description",
        )

        yield Vertical(
            VerticalScroll(
                Vertical(
                    Horizontal(
                        Static("Existing Evaluations", classes="section-title"),
                        classes="section-header-with-button",
                    ),
                    Static(id="existing-evaluations-summary", classes="info-text"),
                    DataTable(id="existing-evaluations-table"),
                    id="existing-evaluations-panel",
                ),
                Vertical(
                    Horizontal(
                        Static("Create New Evaluation", classes="section-title"),
                        classes="section-header-with-button",
                    ),
                    Static("Evaluation Templates", classes="section-title"),
                    DataTable(id="evaluation-templates-table"),
                    Horizontal(
                        Button("Select All Templates", id="btn-select-all-templates", variant="primary"),
                        Button("Clear Templates", id="btn-clear-templates", variant="default"),
                    ),
                    Static("Evaluation Model", classes="section-title"),
                    Horizontal(
                        Select([], id="evaluation-model", allow_blank=True),
                        Button("Refresh Models", id="btn-refresh-models", variant="primary"),
                    ),
                    Static("Agents", classes="section-title"),
                    DataTable(id="evaluation-agents-table"),
                    Horizontal(
                        Button("Refresh Agents [R]", id="btn-refresh-agents", variant="primary"),
                        Button("Select All Agents", id="btn-select-all-agents", variant="default"),
                        Button("Clear Agents", id="btn-clear-agents", variant="default"),
                    ),
                    Horizontal(
                        Button("Run Evaluations [Enter]", id="btn-run", variant="success"),
                        id="evaluation-run-buttons",
                    ),
                    Static("Progress", classes="section-title"),
                    ProgressBar(id="evaluation-progress", total=100, show_eta=False),
                    Static("Ready", id="evaluation-status", classes="info-text"),
                    Static("Execution Log", classes="section-title"),
                    Log(id="evaluation-log", auto_scroll=True),
                    id="create-evaluations-panel",
                ),
                id="evaluation-scroll",
            ),
            Horizontal(
                Button("Back [Esc]", id="btn-back"),
                id="evaluation-footer",
            ),
            id="evaluation-container",
        )

    def on_mount(self) -> None:
        """Initialize tables."""
        templates_table = self.query_one("#evaluation-templates-table", DataTable)
        templates_table.add_columns("Sel", "ID", "Name", "Evaluators")
        templates_table.cursor_type = "row"
        agents_table = self.query_one("#evaluation-agents-table", DataTable)
        agents_table.add_columns("Sel", "Name", "Model")
        agents_table.cursor_type = "row"
        existing_table = self.query_one("#existing-evaluations-table", DataTable)
        existing_table.add_columns("Template", "Agent", "Status", "Run ID", "Report")
        existing_table.cursor_type = "row"

        self._load_templates()
        self._load_existing_evaluations()
        self.action_refresh_models()
        self.action_refresh_agents()

    def on_screen_resume(self) -> None:
        """Refresh evaluation history when returning to the screen."""
        self._load_existing_evaluations()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id
        if button_id == "btn-refresh-agents":
            self.action_refresh_agents()
        elif button_id == "btn-refresh-models":
            self.action_refresh_models()
        elif button_id == "btn-select-all-templates":
            self.action_select_all_templates()
        elif button_id == "btn-clear-templates":
            self.action_clear_templates()
        elif button_id == "btn-select-all-agents":
            self.action_select_all_agents()
        elif button_id == "btn-clear-agents":
            self.action_clear_agents()
        elif button_id == "btn-run":
            self.action_run_evaluations()
        elif button_id == "btn-back":
            self.app.pop_screen()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Toggle selection for templates and agents."""
        table = event.data_table
        row_key = event.row_key
        row_data = table.get_row(row_key)

        if table.id == "evaluation-templates-table":
            template_id = row_data[1] if row_data else None
            if template_id:
                if template_id in self.selected_template_ids:
                    self.selected_template_ids.discard(template_id)
                else:
                    self.selected_template_ids.add(template_id)
                self._populate_templates_table()

        if table.id == "evaluation-agents-table":
            agent_name = row_data[1] if row_data else None
            if agent_name:
                if agent_name in self.selected_agent_names:
                    self.selected_agent_names.discard(agent_name)
                else:
                    self.selected_agent_names.add(agent_name)
                self._populate_agents_table()

    def _load_templates(self) -> None:
        """Load evaluation templates."""
        self.templates = self.template_loader.list_templates()
        self._populate_templates_table()

    def _load_existing_evaluations(self) -> None:
        """Load evaluation runs from state."""
        if self.is_loading_evaluations:
            return
        self.refresh_evaluations_async()

    @work(thread=True)
    def refresh_evaluations_async(self) -> None:
        """Load evaluation runs from the project in a background thread."""
        self.is_loading_evaluations = True
        self.app.call_from_thread(self._update_existing_evaluations_summary, "Loading evaluations...")

        try:
            engine = EvaluationEngine()
            remote_runs = engine.list_recent_runs()
            local_runs = list(reversed(get_state_manager().state.evaluation_runs))
            merged = self._merge_evaluation_runs(remote_runs, local_runs)
            summary = f"{len(merged)} evaluation run(s) in this project"
            self.app.call_from_thread(self._render_existing_evaluations, merged, summary)
        except Exception as exc:
            local_runs = list(reversed(get_state_manager().state.evaluation_runs))
            summary = f"{len(local_runs)} evaluation run(s) in this session"
            self.app.call_from_thread(self._render_existing_evaluations, local_runs, summary)
            self.app.call_from_thread(
                self.notify,
                f"Unable to load project evaluations: {exc}",
                severity="warning",
            )
        finally:
            self.is_loading_evaluations = False

    def _render_existing_evaluations(self, runs, summary_message: str) -> None:
        """Render the existing evaluations table."""
        table = self.query_one("#existing-evaluations-table", DataTable)
        table.clear()

        if not runs:
            self._update_existing_evaluations_summary("No evaluations yet")
            return

        for run in runs:
            run_id = run.get("run_id") or "N/A"
            run_id_display = f"{run_id[:12]}..." if len(run_id) > 12 else run_id
            report_status = "Yes" if run.get("report_url") else "No"
            evaluation_name = run.get("evaluation_name") or run.get("evaluation_id") or "N/A"
            table.add_row(
                evaluation_name,
                run.get("agent_name", "N/A"),
                run.get("run_status", "Unknown"),
                run_id_display,
                report_status,
            )

        self._update_existing_evaluations_summary(summary_message)

    def _merge_evaluation_runs(self, primary_runs, secondary_runs):
        """Merge run lists, keeping the newest entries first."""
        merged = []
        seen = set()
        combined = (primary_runs or []) + (secondary_runs or [])
        for run in combined:
            run_id = run.get("run_id")
            key = run_id or (run.get("evaluation_id"), run.get("agent_name"))
            if key in seen:
                continue
            seen.add(key)
            merged.append(run)
        merged.sort(key=self._run_sort_key, reverse=True)
        return merged

    def _run_sort_key(self, run):
        created_at = run.get("created_at")
        if isinstance(created_at, (int, float)):
            return created_at
        return 0

    def _update_existing_evaluations_summary(self, message: str) -> None:
        """Update the existing evaluations summary."""
        summary = self.query_one("#existing-evaluations-summary", Static)
        summary.update(message)

    def _populate_templates_table(self) -> None:
        """Render templates table."""
        table = self.query_one("#evaluation-templates-table", DataTable)
        table.clear()
        self.template_row_keys.clear()

        for template in self.templates:
            evaluators = ", ".join([ev.name for ev in template.evaluators]) or "None"
            is_selected = template.id in self.selected_template_ids
            row_key = table.add_row(
                "[X]" if is_selected else "[ ]",
                template.id,
                template.display_name,
                evaluators,
            )
            self.template_row_keys[template.id] = row_key

    def _populate_agents_table(self, agents=None) -> None:
        """Render agents table."""
        table = self.query_one("#evaluation-agents-table", DataTable)
        table.clear()
        self.agent_row_keys.clear()

        agents = agents or getattr(self, "agents", [])
        for agent in agents:
            name = agent.get("name", "Unknown")
            is_selected = name in self.selected_agent_names
            row_key = table.add_row(
                "[X]" if is_selected else "[ ]",
                name,
                agent.get("model", "N/A"),
            )
            self.agent_row_keys[name] = row_key

    def action_refresh_agents(self) -> None:
        """Refresh agents list."""
        if self.is_loading_agents:
            self.notify("Already loading agents...", severity="warning")
            return
        self.refresh_agents_async()

    def action_refresh_models(self) -> None:
        """Refresh model list."""
        if self.is_loading_models:
            self.notify("Already loading models...", severity="warning")
            return
        self.refresh_models_async()

    @work(thread=True)
    def refresh_agents_async(self) -> None:
        """Load agents in background thread."""
        self.is_loading_agents = True
        self.app.call_from_thread(self._update_status, "Loading agents...")

        try:
            manager = AgentManager()
            agents = manager.list_agents()
            self.agents = agents
            self.app.call_from_thread(self._populate_agents_table, agents)
            self.app.call_from_thread(
                self._update_status,
                f"Loaded {len(agents)} agents",
            )
        except Exception as exc:
            self.app.call_from_thread(self._update_status, f"Error: {exc}")
            self.app.call_from_thread(self.notify, f"Error: {exc}", severity="error")
        finally:
            self.is_loading_agents = False

    @work(thread=True)
    def refresh_models_async(self) -> None:
        """Load models in background thread."""
        self.is_loading_models = True
        self.app.call_from_thread(self._update_status, "Loading models...")

        try:
            models = self.model_manager.list_available_models(refresh=True)
            self.models = models
            self.app.call_from_thread(self._populate_models_select, models)
            self.app.call_from_thread(
                self._update_status,
                f"Loaded {len(models)} model(s)",
            )
        except Exception as exc:
            self.app.call_from_thread(self._update_status, f"Error: {exc}")
            self.app.call_from_thread(self.notify, f"Error: {exc}", severity="error")
        finally:
            self.is_loading_models = False


    def action_select_all_templates(self) -> None:
        """Select all evaluation templates."""
        self.selected_template_ids = {template.id for template in self.templates}
        self._populate_templates_table()

    def action_clear_templates(self) -> None:
        """Clear template selection."""
        self.selected_template_ids.clear()
        self._populate_templates_table()

    def action_select_all_agents(self) -> None:
        """Select all agents."""
        agents = getattr(self, "agents", [])
        self.selected_agent_names = {agent.get("name", "") for agent in agents if agent.get("name")}
        self._populate_agents_table()

    def action_clear_agents(self) -> None:
        """Clear agent selection."""
        self.selected_agent_names.clear()
        self._populate_agents_table()

    def action_run_evaluations(self) -> None:
        """Run evaluations."""
        if self.evaluation_running:
            self.notify("Evaluation already running", severity="warning")
            return
        if not self.selected_template_ids:
            self.notify("Select at least one evaluation template", severity="warning")
            return
        if not self.selected_agent_names:
            self.notify("Select at least one agent", severity="warning")
            return

        self.run_evaluations_async()

    @work(thread=True)
    def run_evaluations_async(self) -> None:
        """Run evaluations in background thread."""
        self.evaluation_running = True
        self.app.call_from_thread(self._update_status, "Starting evaluations...")
        self.app.call_from_thread(self._reset_progress)
        self.app.call_from_thread(self._log, "[*] Starting evaluations")

        def progress_callback(current, total, message):
            self.app.call_from_thread(self._update_progress, current, total, message)

        def log_callback(message):
            self.app.call_from_thread(self._log, message)

        try:
            model_select = self.query_one("#evaluation-model", Select)
            engine = EvaluationEngine()
            results = engine.run(
                template_ids=sorted(self.selected_template_ids),
                agent_names=sorted(self.selected_agent_names),
                model_deployment_name=model_select.value or None,
                progress_callback=progress_callback,
                log_callback=log_callback,
            )
            for run_summary in results:
                self.app.call_from_thread(get_state_manager().add_evaluation_run, run_summary)
            self.app.call_from_thread(self._load_existing_evaluations)
            self.app.call_from_thread(self._update_status, "Evaluations completed")
            self.app.call_from_thread(self.notify, "Evaluations completed")
        except Exception as exc:
            self.app.call_from_thread(self._update_status, f"Error: {exc}")
            self.app.call_from_thread(self.notify, f"Error: {exc}", severity="error")
        finally:
            self.evaluation_running = False

    def _update_status(self, message: str) -> None:
        """Update status message."""
        status = self.query_one("#evaluation-status", Static)
        status.update(message)

    def _reset_progress(self) -> None:
        """Reset progress bar."""
        progress = self.query_one("#evaluation-progress", ProgressBar)
        progress.update(total=100, progress=0)

    def _update_progress(self, current: int, total: int, message: str) -> None:
        """Update progress bar and status."""
        progress = self.query_one("#evaluation-progress", ProgressBar)
        status = self.query_one("#evaluation-status", Static)
        progress.update(total=total, progress=current)
        status.update(message)

    def _log(self, message: str) -> None:
        """Write to log."""
        log = self.query_one("#evaluation-log", Log)
        log.write_line(message)

    def _populate_models_select(self, models) -> None:
        """Populate model dropdown."""
        select = self.query_one("#evaluation-model", Select)
        options = [(model.deployment_name, model.deployment_name) for model in models]
        select.set_options(options)
        if options:
            select.value = options[0][1]
