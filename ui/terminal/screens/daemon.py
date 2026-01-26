"""
Daemon simulation screen for the Textual TUI application.

Allows users to run continuous background simulations that mimic
production traffic patterns to AI agents.
"""

from collections import deque
from datetime import datetime, timedelta
import time

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Button, Log, Select, DataTable
from textual.containers import Vertical, Horizontal
from textual import work
from textual.timer import Timer

from ui.shared.state_manager import get_state_manager, get_state
from ui.terminal.widgets.rpm_chart import RPMChart
from src.core.daemon_runner import DaemonConfig
from src.core.daemon_service import DaemonService
from src.core.agent_manager import AgentManager
from src.models.agent import CreatedAgent
from src.templates.template_loader import TemplateLoader


class DaemonScreen(Screen):
    """Screen for running continuous daemon simulations."""

    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("s", "start_daemon", "Start"),
        ("x", "stop_daemon", "Stop"),
    ]

    DEFAULT_CSS = """
    DaemonScreen {
        layout: vertical;
    }

    #daemon-header {
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

    #config-row {
        height: auto;
        padding: 1;
        margin: 0 0 1 0;
        border: solid $secondary;
        background: $background;
    }

    #config-row Horizontal {
        height: auto;
        margin-bottom: 1;
    }

    #config-row Select {
        width: 1fr;
        min-width: 50;
    }

    #daemon-setup {
        height: auto;
        padding: 0 1;
        margin: 0 0 1 0;
        border: solid $secondary;
        background: $background;
    }

    #daemon-setup Horizontal {
        height: auto;
        margin-bottom: 1;
    }

    #daemon-agents-table {
        height: 8;
        min-height: 6;
        border: solid $secondary;
        background: $background;
        margin-bottom: 1;
    }

    .input-label {
        width: 14;
        padding-right: 1;
    }

    #metrics-panel {
        height: auto;
        max-height: 16;
        padding: 0 1;
        margin: 1 0;
        border: solid $primary;
        background: $background;
    }

    #metrics-grid {
        height: auto;
    }

    .metric-label {
        width: 16;
        text-style: bold;
    }

    .metric-value {
        width: 12;
    }

    #status-indicator {
        text-style: bold;
        padding: 1;
    }

    .status-running {
        color: $success;
    }

    .status-stopped {
        color: $error;
    }

    #log-panel {
        height: 1fr;
        min-height: 10;
        padding: 0 1;
    }

    #rpm-panel {
        height: auto;
        padding: 0 1;
        margin: 1 0;
    }

    #rpm-subcharts {
        height: auto;
    }

    #rpm-subcharts RPMChart {
        width: 1fr;
    }

    RPMChart.requests-chart-large {
        height: 16;
        min-height: 16;
    }

    RPMChart.requests-chart-small {
        height: 12;
        min-height: 12;
    }

    #daemon-log {
        height: 1fr;
        border: solid $secondary;
        background: $background;
    }
    """

    def __init__(self):
        super().__init__()
        self.daemon_service = DaemonService()
        self._daemon_running = False
        self._history_seeded = False
        self.metrics_timer: Timer = None
        self.template_loader = TemplateLoader()
        self.profiles = []
        self.selected_profile_id = None
        self.selected_profile = None
        self.agents = []
        self.selected_agent_names = set()
        self.agent_row_keys = {}
        self.is_loading_agents = False
        self.bucket_seconds = 5.0
        self.max_buckets = 120
        self.req_labels = deque(maxlen=self.max_buckets)
        self.req_buckets_total = deque(maxlen=self.max_buckets)
        self.req_buckets_ops = deque(maxlen=self.max_buckets)
        self.req_buckets_guard = deque(maxlen=self.max_buckets)
        self._bucket_deadline: float | None = None
        self._bucket_label_time: datetime | None = None
        self._bucket_total = 0
        self._bucket_ops = 0
        self._bucket_guard = 0
        self._last_total_calls: int | None = None
        self._last_total_ops: int | None = None
        self._last_total_guard: int | None = None

    def action_go_back(self) -> None:
        """Go back to previous screen."""
        self.app.pop_screen()

    def compose(self) -> ComposeResult:
        yield Static("Daemon Simulation", id="title", classes="screen-title")
        yield Static("Simulate continuous production traffic to AI agents", classes="description")

        yield Horizontal(
            Button("Start [S]", id="btn-start", variant="success"),
            Button("Stop [X]", id="btn-stop", variant="error"),
            Button("Back [Esc]", id="btn-back"),
            id="button-bar",
        )

        yield Vertical(
            Static("Configuration", classes="section-title"),
            Horizontal(
                Static("Profile:", classes="input-label"),
                Select([], id="daemon-profile", allow_blank=False),
            ),
            Horizontal(
                Static("Traffic Rate:", classes="input-label"),
                Select(
                    [
                        ("Light - 60 calls/min", "light"),
                        ("Medium - 200 calls/min (Recommended)", "medium"),
                        ("Heavy - 500 calls/min", "heavy"),
                        ("Stress - 1000 calls/min", "stress"),
                    ],
                    value="medium",
                    id="traffic-rate",
                    allow_blank=False,
                ),
            ),
            Horizontal(
                Static("Test Type:", classes="input-label"),
                Select(
                    [
                        ("Operations Only - Test agent responses", "operations"),
                        ("Guardrails Only - Test safety filters", "guardrails"),
                        ("Both - Mixed workload (Recommended)", "both"),
                    ],
                    value="both",
                    id="test-type",
                    allow_blank=False,
                ),
            ),
            Horizontal(
                Static("Variance:", classes="input-label"),
                Select(
                    [
                        ("Low - +/-10%", "10"),
                        ("Medium - +/-20% (Recommended)", "20"),
                        ("High - +/-50%", "50"),
                    ],
                    value="20",
                    id="traffic-variance",
                    allow_blank=False,
                ),
            ),
            id="config-row",
        )

        yield Vertical(
            Static("Agents", classes="section-title"),
            DataTable(id="daemon-agents-table"),
            Horizontal(
                Button("Refresh Agents", id="btn-refresh-agents", variant="primary"),
                Button("Select All", id="btn-select-all-agents", variant="default"),
                Button("Clear", id="btn-clear-agents", variant="default"),
            ),
            id="daemon-setup",
        )

        yield Vertical(
            Static(id="status-indicator"),
            Horizontal(
                Vertical(
                    Horizontal(
                        Static("Total Calls:", classes="metric-label"),
                        Static("0", id="metric-total-calls", classes="metric-value"),
                    ),
                    Horizontal(
                        Static("Success Rate:", classes="metric-label"),
                        Static("0%", id="metric-success-rate", classes="metric-value"),
                    ),
                    Horizontal(
                        Static("Avg Latency:", classes="metric-label"),
                        Static("0ms", id="metric-latency", classes="metric-value"),
                    ),
                    Horizontal(
                        Static("Daemon PID:", classes="metric-label"),
                        Static("N/A", id="metric-daemon-pid", classes="metric-value"),
                    ),
                ),
                Vertical(
                    Horizontal(
                        Static("Calls/min:", classes="metric-label"),
                        Static("0", id="metric-calls-per-min", classes="metric-value"),
                    ),
                    Horizontal(
                        Static("Operations:", classes="metric-label"),
                        Static("0", id="metric-operations", classes="metric-value"),
                    ),
                    Horizontal(
                        Static("Guardrails:", classes="metric-label"),
                        Static("0", id="metric-guardrails", classes="metric-value"),
                    ),
                    Horizontal(
                        Static("Last Update:", classes="metric-label"),
                        Static("N/A", id="metric-last-update", classes="metric-value"),
                    ),
                ),
                Vertical(
                    Horizontal(
                        Static("Batches:", classes="metric-label"),
                        Static("0", id="metric-batches", classes="metric-value"),
                    ),
                    Horizontal(
                        Static("Runtime:", classes="metric-label"),
                        Static("0s", id="metric-runtime", classes="metric-value"),
                    ),
                    Horizontal(
                        Static("Variance:", classes="metric-label"),
                        Static("+/-20%", id="metric-load-profile", classes="metric-value"),
                    ),
                    Horizontal(
                        Static("Heartbeat Age:", classes="metric-label"),
                        Static("N/A", id="metric-heartbeat-age", classes="metric-value"),
                    ),
                ),
                id="metrics-grid",
            ),
            id="metrics-panel",
        )

        yield Vertical(
            Static("Request Rate (5s buckets)", classes="section-title"),
            RPMChart(
                "Total Requests / 5s",
                id="req-total",
                accent="cyan",
                unit="req/5s",
                classes="requests-chart-large",
            ),
            Horizontal(
                RPMChart(
                    "Ops / 5s",
                    id="req-ops",
                    accent="green",
                    unit="req/5s",
                    classes="requests-chart-small",
                ),
                RPMChart(
                    "Guard / 5s",
                    id="req-guard",
                    accent="yellow",
                    unit="req/5s",
                    classes="requests-chart-small",
                ),
                id="rpm-subcharts",
            ),
            id="rpm-panel",
        )

        yield Vertical(
            Static("Log:", classes="section-title"),
            Log(id="daemon-log", auto_scroll=True),
            id="log-panel",
        )

    def on_mount(self) -> None:
        """Initialize the screen."""
        agents_table = self.query_one("#daemon-agents-table", DataTable)
        agents_table.add_columns("Sel", "Name", "Model")
        agents_table.cursor_type = "row"

        state = get_state()
        if state.current_profile_id:
            self.selected_profile_id = state.current_profile_id
            self.selected_profile = state.current_profile

        self._load_profiles()
        self.action_refresh_agents()
        self._update_status_indicator(False)
        self._check_prerequisites()
        self._reset_requests_dashboard()
        self._sync_daemon_status()

        # Start metrics refresh timer
        self.metrics_timer = self.set_interval(1.0, self._refresh_metrics)

    def _sync_daemon_status(self) -> None:
        """Sync daemon status/metrics from the background service."""
        running = self.daemon_service.is_running()
        self._daemon_running = running
        self._update_status_indicator(running)
        if running:
            metrics = self.daemon_service.read_metrics()
            if metrics:
                history = self.daemon_service.read_history(limit=self.max_buckets + 1)
                if history:
                    self._seed_requests_dashboard_from_history_samples(history, metrics)
                    self._history_seeded = True
                self._update_metrics_display(metrics)
                get_state_manager().update_daemon_metrics(metrics)
            get_state_manager().start_daemon()
        else:
            get_state_manager().stop_daemon()

    def on_unmount(self) -> None:
        """Cleanup when screen is unmounted."""
        if self.metrics_timer:
            self.metrics_timer.stop()

    def _check_prerequisites(self) -> None:
        """Check if prerequisites are met."""
        log = self.query_one("#daemon-log", Log)

        log.write_line("[*] Daemon Simulation Ready")
        log.write_line("-" * 40)
        log.write_line("[*] Runs as a background process until stopped")

        if not self.selected_profile:
            log.write_line("[!] Warning: No profile selected")
        else:
            log.write_line(f"[+] Profile: {self.selected_profile.metadata.name}")

        if self.selected_agent_names:
            log.write_line(f"[+] Selected Agents: {len(self.selected_agent_names)}")
        else:
            log.write_line("[!] Warning: No agents selected")

        log.write_line("-" * 40)
        log.write_line("[*] Press [S] or click Start to begin")

    def _update_status_indicator(self, is_running: bool) -> None:
        """Update the status indicator."""
        indicator = self.query_one("#status-indicator", Static)
        if is_running:
            indicator.update("Status: RUNNING")
            indicator.remove_class("status-stopped")
            indicator.add_class("status-running")
        else:
            indicator.update("Status: STOPPED")
            indicator.remove_class("status-running")
            indicator.add_class("status-stopped")

    def _refresh_metrics(self) -> None:
        """Refresh the metrics display."""
        running = self.daemon_service.is_running()
        if running:
            if not self._daemon_running:
                self._history_seeded = False
            metrics = self.daemon_service.read_metrics()
            if metrics:
                if not self._history_seeded:
                    history = self.daemon_service.read_history(limit=self.max_buckets + 1)
                    if history:
                        self._seed_requests_dashboard_from_history_samples(history, metrics)
                        self._history_seeded = True
                self._update_metrics_display(metrics)
                get_state_manager().update_daemon_metrics(metrics)
            if not self._daemon_running:
                self._daemon_running = True
                self._update_status_indicator(True)
                get_state_manager().start_daemon()
        elif self._daemon_running:
            self._daemon_running = False
            self._update_status_indicator(False)
            get_state_manager().stop_daemon()

    def _update_metrics_display(self, metrics: dict) -> None:
        """Update the metrics display widgets."""
        self._update_requests_dashboard(metrics)
        self.query_one("#metric-total-calls", Static).update(str(metrics.get("total_calls", 0)))
        self.query_one("#metric-success-rate", Static).update(f"{metrics.get('success_rate', 0):.1f}%")
        self.query_one("#metric-latency", Static).update(f"{metrics.get('avg_latency_ms', 0):.0f}ms")
        self.query_one("#metric-calls-per-min", Static).update(f"{metrics.get('calls_per_minute', 0):.1f}")
        self.query_one("#metric-operations", Static).update(str(metrics.get("total_operations", 0)))
        self.query_one("#metric-guardrails", Static).update(str(metrics.get("total_guardrails", 0)))
        self.query_one("#metric-batches", Static).update(str(metrics.get("batches_completed", 0)))
        self.query_one("#metric-runtime", Static).update(metrics.get("runtime", "0s"))
        self.query_one("#metric-load-profile", Static).update(
            metrics.get("traffic_variance") or metrics.get("current_load_profile", "+/-20%")
        )
        saved_at = metrics.get("saved_at")
        self.query_one("#metric-last-update", Static).update(saved_at.split(".")[0] if saved_at else "N/A")
        self.query_one("#metric-heartbeat-age", Static).update(self._format_heartbeat_age(saved_at))
        self.query_one("#metric-daemon-pid", Static).update(str(metrics.get("pid") or "N/A"))

    def _reset_requests_dashboard(self) -> None:
        """Clear 5s bucket history and reset chart display."""
        self.req_labels.clear()
        self.req_buckets_total.clear()
        self.req_buckets_ops.clear()
        self.req_buckets_guard.clear()
        self._bucket_deadline = None
        self._bucket_label_time = None
        self._bucket_total = 0
        self._bucket_ops = 0
        self._bucket_guard = 0
        self._last_total_calls = None
        self._last_total_ops = None
        self._last_total_guard = None
        self.query_one("#req-total", RPMChart).set_series([], labels=[], subtitle="0 req/5s • 0.0 rpm")
        self.query_one("#req-ops", RPMChart).set_series([], labels=[], subtitle="0 req/5s • 0.0 rpm")
        self.query_one("#req-guard", RPMChart).set_series([], labels=[], subtitle="0 req/5s • 0.0 rpm")

    def _seed_requests_dashboard_from_history_samples(self, history: list[dict], metrics: dict) -> None:
        """Seed the requests chart from persisted daemon history samples."""
        if not history:
            return

        self.req_labels.clear()
        self.req_buckets_total.clear()
        self.req_buckets_ops.clear()
        self.req_buckets_guard.clear()

        prev = None
        for sample in history[-self.max_buckets:]:
            total_calls = int(sample.get("total_calls", 0) or 0)
            total_ops = int(sample.get("total_operations", 0) or 0)
            total_guard = int(sample.get("total_guardrails", 0) or 0)
            if prev is None:
                prev = {
                    "total_calls": total_calls,
                    "total_operations": total_ops,
                    "total_guardrails": total_guard,
                }
                continue

            delta_calls = max(0, total_calls - prev["total_calls"])
            delta_ops = max(0, total_ops - prev["total_operations"])
            delta_guard = max(0, total_guard - prev["total_guardrails"])
            timestamp = sample.get("timestamp", "")
            label = timestamp.split("T")[-1].split(".")[0] if timestamp else ""
            self.req_labels.append(label or datetime.now().strftime("%H:%M:%S"))
            self.req_buckets_total.append(delta_calls)
            self.req_buckets_ops.append(delta_ops)
            self.req_buckets_guard.append(delta_guard)
            prev = {
                "total_calls": total_calls,
                "total_operations": total_ops,
                "total_guardrails": total_guard,
            }

        self._bucket_deadline = time.monotonic() + self.bucket_seconds
        self._bucket_label_time = datetime.now().replace(microsecond=0) + timedelta(seconds=self.bucket_seconds)
        self._bucket_total = 0
        self._bucket_ops = 0
        self._bucket_guard = 0
        self._last_total_calls = metrics.get("total_calls", 0)
        self._last_total_ops = metrics.get("total_operations", 0)
        self._last_total_guard = metrics.get("total_guardrails", 0)
        self._update_requests_dashboard(metrics)

    def _format_heartbeat_age(self, saved_at: str | None) -> str:
        """Human-friendly age since last daemon metrics flush."""
        if not saved_at:
            return "N/A"
        try:
            last = datetime.fromisoformat(saved_at)
        except Exception:
            return "N/A"
        age_s = max(0, int((datetime.now() - last).total_seconds()))
        if age_s < 60:
            return f"{age_s}s"
        age_m = age_s // 60
        if age_m < 60:
            return f"{age_m}m"
        return f"{age_m // 60}h {age_m % 60}m"

    def _update_requests_dashboard(self, metrics: dict) -> None:
        total_calls = int(metrics.get("total_calls", 0) or 0)
        total_ops = int(metrics.get("total_operations", 0) or 0)
        total_guard = int(metrics.get("total_guardrails", 0) or 0)

        now = time.monotonic()
        if self._bucket_deadline is None:
            self._bucket_deadline = now + self.bucket_seconds
            self._bucket_label_time = datetime.now().replace(microsecond=0) + timedelta(seconds=self.bucket_seconds)
            self._last_total_calls = total_calls
            self._last_total_ops = total_ops
            self._last_total_guard = total_guard

        delta_calls = total_calls - (self._last_total_calls or 0)
        delta_ops = total_ops - (self._last_total_ops or 0)
        delta_guard = total_guard - (self._last_total_guard or 0)

        self._last_total_calls = total_calls
        self._last_total_ops = total_ops
        self._last_total_guard = total_guard

        if delta_calls < 0 or delta_ops < 0 or delta_guard < 0:
            self._reset_requests_dashboard()
            self._bucket_deadline = now + self.bucket_seconds
            self._bucket_label_time = datetime.now().replace(microsecond=0) + timedelta(seconds=self.bucket_seconds)
            self._last_total_calls = total_calls
            self._last_total_ops = total_ops
            self._last_total_guard = total_guard
            delta_calls = 0
            delta_ops = 0
            delta_guard = 0

        self._bucket_total += delta_calls
        self._bucket_ops += delta_ops
        self._bucket_guard += delta_guard

        # Check if bucket deadline passed and finalize completed buckets
        while self._bucket_deadline is not None and now >= self._bucket_deadline:
            bucket_end = self._bucket_label_time or datetime.now().replace(microsecond=0)
            self.req_labels.append(bucket_end.strftime("%H:%M:%S"))
            self.req_buckets_total.append(self._bucket_total)
            self.req_buckets_ops.append(self._bucket_ops)
            self.req_buckets_guard.append(self._bucket_guard)
            self._bucket_total = 0
            self._bucket_ops = 0
            self._bucket_guard = 0
            self._bucket_deadline += self.bucket_seconds
            self._bucket_label_time = bucket_end + timedelta(seconds=self.bucket_seconds)

        # Build series with historical data plus current live bucket
        labels = list(self.req_labels)
        series_total = list(self.req_buckets_total)
        series_ops = list(self.req_buckets_ops)
        series_guard = list(self.req_buckets_guard)

        # Append live in-progress bucket as the last point
        live_label = (self._bucket_label_time or datetime.now().replace(microsecond=0)).strftime("%H:%M:%S")
        labels.append(live_label)
        series_total.append(self._bucket_total)
        series_ops.append(self._bucket_ops)
        series_guard.append(self._bucket_guard)

        rpm_multiplier = 60.0 / self.bucket_seconds
        live_total = self._bucket_total
        live_ops = self._bucket_ops
        live_guard = self._bucket_guard

        self.query_one("#req-total", RPMChart).set_series(
            series_total,
            labels=labels,
            subtitle=f"{live_total} req/5s • {live_total * rpm_multiplier:.1f} rpm",
        )
        self.query_one("#req-ops", RPMChart).set_series(
            series_ops,
            labels=labels,
            subtitle=f"{live_ops} req/5s • {live_ops * rpm_multiplier:.1f} rpm",
        )
        self.query_one("#req-guard", RPMChart).set_series(
            series_guard,
            labels=labels,
            subtitle=f"{live_guard} req/5s • {live_guard * rpm_multiplier:.1f} rpm",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "btn-refresh-agents":
            self.action_refresh_agents()
        elif button_id == "btn-select-all-agents":
            self.action_select_all_agents()
        elif button_id == "btn-clear-agents":
            self.action_clear_agents()
        elif button_id == "btn-start":
            self.action_start_daemon()
        elif button_id == "btn-stop":
            self.action_stop_daemon()
        elif button_id == "btn-back":
            self.app.pop_screen()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Toggle selection when an agent row is selected."""
        table = event.data_table
        if table.id != "daemon-agents-table":
            return

        row_data = table.get_row(event.row_key)
        agent_name = row_data[1] if row_data else None
        if not agent_name:
            return

        if agent_name in self.selected_agent_names:
            self.selected_agent_names.discard(agent_name)
        else:
            self.selected_agent_names.add(agent_name)

        self._populate_agents_table()

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle profile selection changes."""
        if event.select.id != "daemon-profile":
            return

        profile_id = event.value
        if not profile_id:
            self.selected_profile_id = None
            self.selected_profile = None
            get_state_manager().clear_profile()
            return

        try:
            profile = self.template_loader.load_template(profile_id)
        except Exception as exc:
            self.notify(f"Error loading profile: {exc}", severity="error")
            return

        self.selected_profile_id = profile_id
        self.selected_profile = profile
        get_state_manager().set_profile(profile, profile_id)

    def _load_profiles(self) -> None:
        """Load profile options for selection."""
        template_ids = self.template_loader.list_templates()
        options = []

        for template_id in template_ids:
            try:
                info = self.template_loader.get_template_info(template_id)
                label = f"{info['name']} ({info['id']})"
            except Exception:
                label = template_id
            options.append((label, template_id))

        select = self.query_one("#daemon-profile", Select)
        select.set_options(options)

        if self.selected_profile_id and any(opt[1] == self.selected_profile_id for opt in options):
            select.value = self.selected_profile_id
        elif options:
            # Auto-select first profile if none selected
            first_profile_id = options[0][1]
            select.value = first_profile_id
            try:
                profile = self.template_loader.load_template(first_profile_id)
                self.selected_profile_id = first_profile_id
                self.selected_profile = profile
                get_state_manager().set_profile(profile, first_profile_id)
            except Exception:
                pass

    def action_refresh_agents(self) -> None:
        """Refresh the agents list from the project."""
        if self.is_loading_agents:
            self.notify("Already loading agents...", severity="warning")
            return
        self.refresh_agents_async()

    @work(thread=True)
    def refresh_agents_async(self) -> None:
        """Load agents in a background thread."""
        self.is_loading_agents = True
        self.app.call_from_thread(self.notify, "Loading agents...", severity="information")

        try:
            manager = AgentManager()
            agents = manager.list_agents()
            self.agents = agents
            self.app.call_from_thread(self._populate_agents_table, agents)
            self.app.call_from_thread(self.notify, f"Loaded {len(agents)} agents")
        except Exception as exc:
            self.app.call_from_thread(self.notify, f"Error: {exc}", severity="error")
        finally:
            self.is_loading_agents = False

    def action_select_all_agents(self) -> None:
        """Select all agents."""
        self.selected_agent_names = {
            agent.get("name", "") for agent in self.agents if agent.get("name")
        }
        self._populate_agents_table()

    def action_clear_agents(self) -> None:
        """Clear agent selection."""
        self.selected_agent_names.clear()
        self._populate_agents_table()

    def _populate_agents_table(self, agents=None) -> None:
        """Populate the agents table with selection state."""
        table = self.query_one("#daemon-agents-table", DataTable)
        table.clear()
        self.agent_row_keys.clear()

        agents = agents or self.agents
        for agent in agents:
            name = agent.get("name", "Unknown")
            is_selected = name in self.selected_agent_names
            row_key = table.add_row(
                "[X]" if is_selected else "[ ]",
                name,
                agent.get("model", "N/A"),
            )
            self.agent_row_keys[name] = row_key

    def _to_created_agent(self, agent: dict) -> CreatedAgent:
        """Convert a project agent dict into a CreatedAgent."""
        name = agent.get("name") or "Unknown"
        azure_id = agent.get("id") or ""
        version = agent.get("version")
        try:
            version = int(version) if version is not None else 1
        except (ValueError, TypeError):
            version = 1

        model = agent.get("model") or "unknown"
        parts = name.split("-") if name else []
        org_id = parts[0] if len(parts) >= 1 else "UNKNOWN"
        agent_type = parts[1] if len(parts) >= 2 else None
        agent_id = parts[2] if len(parts) >= 3 else (parts[-1] if parts else "UNKNOWN")

        return CreatedAgent(
            agent_id=agent_id or "UNKNOWN",
            name=name,
            azure_id=azure_id,
            version=version,
            model=model,
            org_id=org_id,
            agent_type=agent_type,
        )

    def _get_selected_agents(self) -> list[CreatedAgent]:
        """Return the selected agents as CreatedAgent objects."""
        selected = []
        for agent in self.agents:
            name = agent.get("name")
            if name and name in self.selected_agent_names:
                selected.append(self._to_created_agent(agent))
        return selected

    def _require_profile(self, log: Log) -> object | None:
        """Return selected profile or emit a user-facing error."""
        if not self.selected_profile:
            self.notify("Select a profile before starting the daemon", severity="error")
            log.write_line("[X] No profile selected. Choose one in Simulation Setup.")
            return None
        return self.selected_profile

    def _get_traffic_config(self, rate: str) -> dict:
        """Convert traffic rate selection to technical parameters.

        Thread calculation: For target RPM with avg API latency of ~3s,
        we need: threads >= (calls_per_batch * avg_latency) / interval
        """
        configs = {
            "light": {  # 60 calls/min (1/sec)
                "interval": 10,
                "calls_min": 10,
                "calls_max": 10,
                "threads": 5,
                "delay": 0.1,
                "label": "Light (60 calls/min)",
            },
            "medium": {  # 200 calls/min (~3/sec)
                "interval": 10,
                "calls_min": 33,
                "calls_max": 33,
                "threads": 15,
                "delay": 0.05,
                "label": "Medium (200 calls/min)",
            },
            "heavy": {  # 500 calls/min (~8/sec)
                "interval": 10,
                "calls_min": 83,
                "calls_max": 83,
                "threads": 30,
                "delay": 0.02,
                "label": "Heavy (500 calls/min)",
            },
            "stress": {  # 1000 calls/min (~17/sec)
                "interval": 10,
                "calls_min": 167,
                "calls_max": 167,
                "threads": 60,
                "delay": 0.01,
                "label": "Stress (1000 calls/min)",
            },
        }
        return configs.get(rate, configs["medium"])

    def _get_test_type_config(self, test_type: str) -> dict:
        """Convert test type selection to operations weight."""
        configs = {
            "operations": {"ops_weight": 100, "label": "Operations Only"},
            "guardrails": {"ops_weight": 0, "label": "Guardrails Only"},
            "both": {"ops_weight": 70, "label": "Both (70% Ops / 30% Guard)"},
        }
        return configs.get(test_type, configs["both"])

    def action_start_daemon(self) -> None:
        """Start the daemon simulation."""
        if self.daemon_service.is_running():
            self.notify("Daemon is already running", severity="warning")
            return

        self._reset_requests_dashboard()
        self._history_seeded = False
        log = self.query_one("#daemon-log", Log)

        # Get user selections
        traffic_rate = self.query_one("#traffic-rate", Select).value or "medium"
        test_type = self.query_one("#test-type", Select).value or "both"
        variance_value = self.query_one("#traffic-variance", Select).value or "20"

        # Convert to technical parameters
        traffic_config = self._get_traffic_config(traffic_rate)
        test_config = self._get_test_type_config(test_type)

        interval = traffic_config["interval"]
        calls_min = traffic_config["calls_min"]
        calls_max = traffic_config["calls_max"]
        threads = traffic_config["threads"]
        delay = traffic_config["delay"]
        ops_weight = test_config["ops_weight"]

        try:
            variance_pct = int(variance_value)
        except ValueError:
            variance_pct = 20

        profile = self._require_profile(log)
        if not profile or not self.selected_profile_id:
            return

        selected_agents = self._get_selected_agents()
        if not selected_agents:
            self.notify("Select at least one agent to start the daemon", severity="error")
            log.write_line("[X] No agents selected. Choose agents in Simulation Setup.")
            return

        log.write_line("")
        log.write_line("=" * 50)
        log.write_line("[>] Starting daemon simulation...")
        log.write_line(f"    Traffic: {traffic_config['label']}")
        log.write_line(f"    Test Type: {test_config['label']}")
        log.write_line(f"    Variance: +/-{variance_pct}%")
        log.write_line(f"    Profile: {profile.metadata.name}")
        log.write_line(f"    Agents: {len(selected_agents)} selected")
        log.write_line("=" * 50)

        def apply_variance(base: int, pct: int) -> tuple[int, int]:
            pct = max(0, min(90, int(pct)))
            lo = max(1, int(base * (100 - pct) / 100))
            hi = max(lo, int(base * (100 + pct) / 100))
            return lo, hi

        base_calls = calls_max
        calls_min, calls_max = apply_variance(base_calls, variance_pct)

        # Create config
        config = DaemonConfig(
            interval_seconds=interval,
            calls_per_batch_min=calls_min,
            calls_per_batch_max=calls_max,
            threads=threads,
            delay=delay,
            operations_weight=ops_weight,
            traffic_variance_pct=variance_pct,
        )

        log.write_line(f"[+] Loaded {len(selected_agents)} agents")

        ok, message = self.daemon_service.start(
            config,
            selected_agents,
            self.selected_profile_id,
            profile.metadata.name,
        )
        if ok:
            self._update_status_indicator(True)
            self._daemon_running = True
            get_state_manager().start_daemon()
            self.notify("Daemon started")
            log.write_line("[+] Daemon started successfully")
        else:
            self.notify(message, severity="error")
            log.write_line(f"[X] {message}")

    def action_stop_daemon(self) -> None:
        """Stop the daemon simulation."""
        if not self.daemon_service.is_running():
            self.notify("Daemon is not running", severity="warning")
            return

        log = self.query_one("#daemon-log", Log)
        log.write_line("")
        log.write_line("[>] Stopping daemon...")

        ok, message = self.daemon_service.stop()
        if ok:
            self._daemon_running = False
            self._update_status_indicator(False)
            get_state_manager().stop_daemon()
            metrics = self.daemon_service.read_metrics()
            log.write_line("[+] Daemon stopped")
            log.write_line("=" * 50)
            if metrics:
                self._update_metrics_display(metrics)
                log.write_line("Final Statistics:")
                log.write_line(f"  Total Calls: {metrics.get('total_calls', 0)}")
                log.write_line(f"  Success Rate: {metrics.get('success_rate', 0):.1f}%")
                log.write_line(f"  Avg Latency: {metrics.get('avg_latency_ms', 0):.1f}ms")
                log.write_line(f"  Runtime: {metrics.get('runtime', '0s')}")
            log.write_line("=" * 50)
            self.notify("Daemon stopped")
        else:
            self.notify(message, severity="error")
            log.write_line(f"[X] {message}")
