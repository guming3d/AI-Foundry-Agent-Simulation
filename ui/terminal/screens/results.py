"""
Results screen for the Textual TUI application.

Displays simulation results and statistics.
"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Button, DataTable
from textual.containers import Vertical, Horizontal, ScrollableContainer

from ui.shared.state_manager import get_state
from src.core import config


class ResultsScreen(Screen):
    """Screen for viewing simulation results."""

    BINDINGS = [
        ("escape", "app.pop_screen()", "Back"),
        ("e", "export_results", "Export"),
    ]

    def compose(self) -> ComposeResult:
        yield Static("Simulation Results", id="title", classes="screen-title")

        # Operations results panel
        yield Vertical(
            Static("[b]Operations Results[/b]", classes="section-title"),
            Static(id="ops-summary"),
            Static("Agent Type Distribution:", classes="section-title"),
            DataTable(id="ops-types-table"),
            Static("Model Distribution:", classes="section-title"),
            DataTable(id="ops-models-table"),
            id="ops-panel",
            classes="results-panel",
        )

        # Guardrails results panel
        yield Vertical(
            Static("[b]Guardrails Results[/b]", classes="section-title"),
            Static(id="guard-summary"),
            Static("Category Statistics:", classes="section-title"),
            DataTable(id="guard-categories-table"),
            Static("Model Statistics:", classes="section-title"),
            DataTable(id="guard-models-table"),
            id="guard-panel",
            classes="results-panel",
        )

        yield Horizontal(
            Button("Export Results [E]", id="btn-export", variant="primary"),
            Button("Back", id="btn-back"),
            id="button-bar",
        )

    def on_mount(self) -> None:
        """Initialize the results display."""
        self._setup_tables()
        self._load_results()

    def on_screen_resume(self) -> None:
        """Refresh results when returning to screen."""
        self._load_results()

    def _setup_tables(self) -> None:
        """Setup the data tables."""
        # Operations tables
        ops_types = self.query_one("#ops-types-table", DataTable)
        ops_types.add_columns("Agent Type", "Calls", "Percentage")

        ops_models = self.query_one("#ops-models-table", DataTable)
        ops_models.add_columns("Model", "Calls", "Percentage")

        # Guardrails tables
        guard_cats = self.query_one("#guard-categories-table", DataTable)
        guard_cats.add_columns("Category", "Total", "Blocked", "Block Rate", "Status")

        guard_models = self.query_one("#guard-models-table", DataTable)
        guard_models.add_columns("Model", "Total", "Blocked", "Block Rate")

    def _load_results(self) -> None:
        """Load results from state."""
        state = get_state()

        # Load operations results
        self._load_operations_results(state.operation_summary)

        # Load guardrails results
        self._load_guardrails_results(state.guardrail_summary)

    def _load_operations_results(self, summary: dict) -> None:
        """Load operations results into display."""
        ops_summary = self.query_one("#ops-summary", Static)

        if not summary:
            ops_summary.update("No operations results available. Run a simulation first.")
            return

        total = summary.get("total_calls", 0)
        success = summary.get("successful_calls", 0)
        failed = summary.get("failed_calls", 0)
        success_rate = summary.get("success_rate", 0)
        avg_latency = summary.get("avg_latency_ms", 0)
        min_latency = summary.get("min_latency_ms", 0)
        max_latency = summary.get("max_latency_ms", 0)

        ops_summary.update(f"""
[b]Total Calls:[/b] {total}
[b]Successful:[/b] {success} ({success_rate:.1f}%)
[b]Failed:[/b] {failed}

[b]Latency:[/b]
  Average: {avg_latency:.2f}ms
  Min: {min_latency:.2f}ms
  Max: {max_latency:.2f}ms
        """)

        # Agent type distribution
        types_table = self.query_one("#ops-types-table", DataTable)
        types_table.clear()

        type_dist = summary.get("agent_type_distribution", {})
        for agent_type, count in sorted(type_dist.items(), key=lambda x: x[1], reverse=True):
            pct = count / total * 100 if total > 0 else 0
            types_table.add_row(agent_type, str(count), f"{pct:.1f}%")

        # Model distribution
        models_table = self.query_one("#ops-models-table", DataTable)
        models_table.clear()

        model_dist = summary.get("model_distribution", {})
        for model, count in sorted(model_dist.items(), key=lambda x: x[1], reverse=True):
            pct = count / total * 100 if total > 0 else 0
            models_table.add_row(model, str(count), f"{pct:.1f}%")

    def _load_guardrails_results(self, summary: dict) -> None:
        """Load guardrails results into display."""
        guard_summary = self.query_one("#guard-summary", Static)

        if not summary:
            guard_summary.update("No guardrail results available. Run a simulation first.")
            return

        total = summary.get("total_tests", 0)
        blocked = summary.get("blocked", 0)
        allowed = summary.get("allowed", 0)
        block_rate = summary.get("overall_block_rate", 0)
        recommendation = summary.get("recommendation", "N/A")

        status_color = "green" if recommendation == "PASS" else "yellow" if recommendation == "REVIEW" else "red"

        guard_summary.update(f"""
[b]Total Tests:[/b] {total}
[b]Blocked:[/b] {blocked} ({block_rate:.1f}%)
[b]Allowed:[/b] {allowed}

[b]Recommendation:[/b] [{status_color}]{recommendation}[/{status_color}]
        """)

        # Category statistics
        cats_table = self.query_one("#guard-categories-table", DataTable)
        cats_table.clear()

        cat_stats = summary.get("category_stats", {})
        for cat, stats in sorted(cat_stats.items(), key=lambda x: x[1].get("block_rate", 0)):
            cat_total = stats.get("total", 0)
            cat_blocked = stats.get("blocked", 0)
            cat_rate = stats.get("block_rate", 0)
            status = "OK" if cat_rate >= 95 else "WARN" if cat_rate >= 80 else "CRITICAL"
            cats_table.add_row(cat, str(cat_total), str(cat_blocked), f"{cat_rate:.1f}%", status)

        # Model statistics
        models_table = self.query_one("#guard-models-table", DataTable)
        models_table.clear()

        model_stats = summary.get("model_stats", {})
        for model, stats in sorted(model_stats.items(), key=lambda x: x[1].get("block_rate", 0)):
            m_total = stats.get("total", 0)
            m_blocked = stats.get("blocked", 0)
            m_rate = stats.get("block_rate", 0)
            models_table.add_row(model, str(m_total), str(m_blocked), f"{m_rate:.1f}%")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "btn-export":
            self.action_export_results()
        elif button_id == "btn-back":
            self.app.pop_screen()

    def action_export_results(self) -> None:
        """Export results to files."""
        state = get_state()

        if state.operation_summary:
            self.notify(f"Operations results saved to {config.SIMULATION_SUMMARY_JSON}")

        if state.guardrail_summary:
            self.notify(f"Guardrail results saved to {config.GUARDRAILS_SUMMARY_JSON}")

        if not state.operation_summary and not state.guardrail_summary:
            self.notify("No results to export", severity="warning")
