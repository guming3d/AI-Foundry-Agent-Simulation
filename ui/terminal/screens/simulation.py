"""
Simulation screen for the Textual TUI application.

Allows users to run simulations and monitor progress.
Supports both one-time simulations and long-running daemon simulations.
"""

from collections import deque
from datetime import datetime, timedelta
import time

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Button, Input, ProgressBar, Log, Select, DataTable, TabbedContent, TabPane
from textual.containers import Vertical, Horizontal, VerticalScroll, Grid
from textual import work
from textual.timer import Timer

from ui.shared.state_manager import get_state_manager, get_state
from ui.terminal.widgets.rpm_chart import RPMChart
from src.core.simulation_engine import SimulationEngine, SimulationConfig
from src.core.daemon_runner import DaemonConfig
from src.core.daemon_service import DaemonService
from src.core import config
from src.core.agent_manager import AgentManager
from src.models.agent import CreatedAgent
from src.templates.template_loader import TemplateLoader


class SimulationScreen(Screen):
    """Screen for running simulations."""

    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("r", "run_current", "Run"),
        ("x", "stop_current", "Stop"),
    ]

    def __init__(self):
        super().__init__()
        self.engine = None
        self.simulation_active = False
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
        yield Static("Simulation Dashboard", id="title", classes="screen-title")

        with Vertical(id="sim-setup", classes="config-section-top"):
            yield Static("Simulation Setup", classes="config-section-title")
            with Horizontal(classes="config-row"):
                yield Static("Profile:", classes="input-label")
                yield Select([], id="sim-profile", allow_blank=True)
                yield Button("Refresh Profiles", id="btn-refresh-profiles", variant="default")
            yield Static("Agents", classes="section-title")
            yield DataTable(id="sim-agents-table")
            with Horizontal(classes="button-row"):
                yield Button("Refresh Agents", id="btn-refresh-agents", variant="primary")
                yield Button("Select All", id="btn-select-all-agents", variant="default")
                yield Button("Clear", id="btn-clear-agents", variant="default")

        with TabbedContent(id="sim-tabs"):
            # Tab 1: One-Time Simulation
            with TabPane("One-Time Simulation", id="tab-onetime"):
                # Type Selection
                with Vertical(id="onetime-type-section"):
                    yield Static("Simulation Type", classes="config-section-title")
                    yield Select(
                        [
                            ("Operations - Test agent API calls", "operations"),
                            ("Guardrails - Test safety filters", "guardrails"),
                            ("Both - Run operations and guardrails", "both"),
                        ],
                        value="operations",
                        id="sim-type",
                        allow_blank=False,
                    )

                # Configuration
                with Vertical(id="onetime-config", classes="config-section"):
                    yield Static("Configuration", classes="config-section-title")
                    with Horizontal(classes="config-row"):
                        yield Static("Number of Calls:", classes="input-label")
                        yield Input(value="50", id="num-calls", type="integer", classes="input-field")
                        yield Static("Total API calls to make", classes="description")
                    with Horizontal(classes="config-row"):
                        yield Static("Threads:", classes="input-label")
                        yield Input(value="3", id="threads", type="integer", classes="input-field")
                        yield Static("Concurrent execution threads", classes="description")
                    with Horizontal(classes="config-row"):
                        yield Static("Delay (seconds):", classes="input-label")
                        yield Input(value="0.5", id="delay", classes="input-field")
                        yield Static("Delay between calls", classes="description")

                # Buttons
                with Horizontal(classes="button-row"):
                    yield Button("Start Simulation", id="btn-onetime-run", variant="primary")
                    yield Button("Stop", id="btn-onetime-stop", variant="error")
                    yield Button("Export Results", id="btn-onetime-export", variant="success")
                yield Button("Back to Home", id="btn-back-onetime", variant="default")

                # Progress
                with Vertical(id="onetime-progress-section"):
                    yield Static("Progress", classes="config-section-title")
                    yield ProgressBar(id="onetime-progress", total=100, show_eta=True)
                    yield Static("Ready to run simulation", id="onetime-status")

                # Log
                with Vertical(id="onetime-log-section"):
                    yield Static("Execution Log", classes="config-section-title")
                    yield Log(id="onetime-log", auto_scroll=True)

                # Back button at bottom of results
                with Horizontal(classes="button-row"):
                    yield Button("Back to Home", id="btn-back-results", variant="default")

            # Tab 2: Long-Running Daemon
            with TabPane("Long-Running Daemon", id="tab-daemon"):
                # Status
                with Vertical(id="daemon-status-section"):
                    yield Static("Daemon Status", classes="config-section-title")
                    yield Static("STOPPED", id="daemon-status", classes="status-stopped")

                # Configuration
                with Vertical(id="daemon-config", classes="config-section"):
                    yield Static("Daemon Configuration", classes="config-section-title")
                    with Horizontal(classes="config-row"):
                        yield Static("Traffic Rate:", classes="input-label")
                        yield Select(
                            [
                                ("Light - 60 calls/min", "light"),
                                ("Medium - 200 calls/min (Recommended)", "medium"),
                                ("Heavy - 500 calls/min", "heavy"),
                                ("Stress - 1000 calls/min", "stress"),
                            ],
                            value="medium",
                            id="daemon-traffic-rate",
                            allow_blank=False,
                        )
                    with Horizontal(classes="config-row"):
                        yield Static("Test Type:", classes="input-label")
                        yield Select(
                            [
                                ("Operations Only - Test agent responses", "operations"),
                                ("Guardrails Only - Test safety filters", "guardrails"),
                                ("Both - Mixed workload (Recommended)", "both"),
                            ],
                            value="both",
                            id="daemon-test-type",
                            allow_blank=False,
                        )
                    with Horizontal(classes="config-row"):
                        yield Static("Variance:", classes="input-label")
                        yield Select(
                            [
                                ("Low - +/-10%", "10"),
                                ("Medium - +/-20% (Recommended)", "20"),
                                ("High - +/-50%", "50"),
                            ],
                            value="20",
                            id="daemon-traffic-variance",
                            allow_blank=False,
                        )

                # Buttons
                with Horizontal(classes="button-row"):
                    yield Button("Start Daemon", id="btn-daemon-start", variant="primary")
                    yield Button("Stop Daemon", id="btn-daemon-stop", variant="error")
                    # yield Button("Back to Home", id="btn-back-daemon", variant="default")

                # Real-time Metrics
                with Vertical(id="daemon-metrics-section"):
                    yield Static("Real-time Metrics", classes="config-section-title")
                    with Grid(id="metrics-grid"):
                        with Vertical(classes="metric-box"):
                            yield Static("Total Calls", classes="metric-header")
                            yield Static("0", id="metric-total-calls", classes="metric-value")
                        with Vertical(classes="metric-box"):
                            yield Static("Target/min", classes="metric-header")
                            yield Static("0.0", id="metric-target-calls-per-min", classes="metric-value")
                        with Vertical(classes="metric-box"):
                            yield Static("Success Rate", classes="metric-header")
                            yield Static("0%", id="metric-success-rate", classes="metric-value")
                        with Vertical(classes="metric-box"):
                            yield Static("Avg Latency", classes="metric-header")
                            yield Static("0ms", id="metric-latency", classes="metric-value")
                        with Vertical(classes="metric-box"):
                            yield Static("P95 Latency", classes="metric-header")
                            yield Static("0ms", id="metric-p95-latency", classes="metric-value")
                        with Vertical(classes="metric-box"):
                            yield Static("Calls/min", classes="metric-header")
                            yield Static("0", id="metric-calls-per-min", classes="metric-value")
                        with Vertical(classes="metric-box"):
                            yield Static("Started/min", classes="metric-header")
                            yield Static("0", id="metric-started-calls-per-min", classes="metric-value")
                        with Vertical(classes="metric-box"):
                            yield Static("Inflight", classes="metric-header")
                            yield Static("0", id="metric-inflight", classes="metric-value")
                        with Vertical(classes="metric-box"):
                            yield Static("Queue", classes="metric-header")
                            yield Static("0", id="metric-queue-depth", classes="metric-value")
                        with Vertical(classes="metric-box"):
                            yield Static("Dropped", classes="metric-header")
                            yield Static("0", id="metric-dropped-calls", classes="metric-value")
                        with Vertical(classes="metric-box"):
                            yield Static("Operations", classes="metric-header")
                            yield Static("0", id="metric-operations", classes="metric-value")
                        with Vertical(classes="metric-box"):
                            yield Static("Guardrails", classes="metric-header")
                            yield Static("0", id="metric-guardrails", classes="metric-value")
                        with Vertical(classes="metric-box"):
                            yield Static("Batches", classes="metric-header")
                            yield Static("0", id="metric-batches", classes="metric-value")
                        with Vertical(classes="metric-box"):
                            yield Static("Runtime", classes="metric-header")
                            yield Static("0s", id="metric-runtime", classes="metric-value")
                        with Vertical(classes="metric-box"):
                            yield Static("Variance", classes="metric-header")
                            yield Static("+/-20%", id="metric-load-profile", classes="metric-value")
                        with Vertical(classes="metric-box"):
                            yield Static("Last Update", classes="metric-header")
                            yield Static("N/A", id="metric-last-update", classes="metric-value")
                        with Vertical(classes="metric-box"):
                            yield Static("Heartbeat Age", classes="metric-header")
                            yield Static("N/A", id="metric-heartbeat-age", classes="metric-value")
                        with Vertical(classes="metric-box"):
                            yield Static("Daemon PID", classes="metric-header")
                            yield Static("N/A", id="metric-daemon-pid", classes="metric-value")

                with Vertical(id="daemon-rpm-section"):
                    yield Static("Request Rate (5s buckets)", classes="config-section-title")
                    yield RPMChart(
                        "Total Requests / 5s",
                        id="req-total",
                        accent="cyan",
                        unit="req/5s",
                        classes="requests-chart-large",
                    )
                    with Horizontal(id="daemon-rpm-subcharts"):
                        yield RPMChart(
                            "Ops / 5s",
                            id="req-ops",
                            accent="green",
                            unit="req/5s",
                            classes="requests-chart-small",
                        )
                        yield RPMChart(
                            "Guard / 5s",
                            id="req-guard",
                            accent="yellow",
                            unit="req/5s",
                            classes="requests-chart-small",
                        )

                # Log
                with Vertical(id="daemon-log-section"):
                    yield Static("Daemon Log", classes="config-section-title")
                    yield Log(id="daemon-log", auto_scroll=True)
                                # Back button at bottom of results
                with Horizontal(classes="button-row"):
                    yield Button("Back to Home", id="btn-back-results", variant="default")

            # Tab 3: Results
            with TabPane("Results", id="tab-results"):
                with VerticalScroll():
                    # Operations Results
                    with Vertical(classes="results-section"):
                        yield Static("OPERATIONS PERFORMANCE", classes="results-header")
                        yield Static(id="ops-summary", classes="summary-text")

                        with Horizontal(classes="table-container"):
                            with Vertical(classes="table-box"):
                                yield Static("Agent Type Distribution", classes="table-title")
                                yield DataTable(id="ops-types-table")
                            with Vertical(classes="table-box"):
                                yield Static("Model Distribution", classes="table-title")
                                yield DataTable(id="ops-models-table")

                    # Guardrails Results
                    with Vertical(classes="results-section"):
                        yield Static("GUARDRAILS & SAFETY", classes="results-header")
                        yield Static(id="guard-summary", classes="summary-text")

                        with Horizontal(classes="table-container"):
                            with Vertical(classes="table-box"):
                                yield Static("Category Statistics", classes="table-title")
                                yield DataTable(id="guard-categories-table")
                            with Vertical(classes="table-box"):
                                yield Static("Model Comparison", classes="table-title")
                                yield DataTable(id="guard-models-table")

                # Back button at bottom of results
                with Horizontal(classes="button-row"):
                    yield Button("Back to Home", id="btn-back-results", variant="default")

    def on_mount(self) -> None:
        """Initialize the screen."""
        agents_table = self.query_one("#sim-agents-table", DataTable)
        agents_table.add_columns("Sel", "Name", "Model")
        agents_table.cursor_type = "row"

        state = get_state()
        if state.current_profile_id:
            self.selected_profile_id = state.current_profile_id
            self.selected_profile = state.current_profile

        self._load_profiles()
        self.action_refresh_agents()
        self._init_onetime_log()
        self._init_daemon_log()
        self._setup_results_tables()
        self._load_results()
        self._reset_requests_dashboard()
        self._sync_daemon_status()
        # Start metrics refresh timer
        self.metrics_timer = self.set_interval(1.0, self._refresh_daemon_metrics)

    def _sync_daemon_status(self) -> None:
        """Sync daemon status/metrics from the background service."""
        running = self.daemon_service.is_running()
        self._daemon_running = running
        self._update_daemon_status(running)
        if running:
            metrics = self.daemon_service.read_metrics()
            if metrics:
                history = self.daemon_service.read_history(limit=self.max_buckets + 1)
                if history:
                    self._seed_requests_dashboard_from_history_samples(history, metrics)
                    self._history_seeded = True
                self._update_daemon_metrics(metrics)
                get_state_manager().update_daemon_metrics(metrics)
            get_state_manager().start_daemon()
        else:
            get_state_manager().stop_daemon()

    def _init_onetime_log(self) -> None:
        """Initialize the one-time simulation log."""
        log = self.query_one("#onetime-log", Log)

        log.write_line("[*] One-Time Simulation")
        log.write_line("=" * 40)

        if not self.selected_profile:
            log.write_line("[!] Warning: No profile selected")
        else:
            log.write_line(f"[+] Profile: {self.selected_profile.metadata.name}")

        if not self.selected_agent_names:
            log.write_line("[!] Warning: No agents selected")
        else:
            log.write_line(f"[+] Selected Agents: {len(self.selected_agent_names)}")

        log.write_line("")
        log.write_line("[*] Configure settings above and click 'Start Simulation'")

    def _init_daemon_log(self) -> None:
        """Initialize the daemon simulation log."""
        log = self.query_one("#daemon-log", Log)

        log.write_line("[*] Long-Running Daemon Simulation")
        log.write_line("=" * 40)
        log.write_line("[*] Simulates production traffic patterns:")
        log.write_line("    - Higher load during business hours")
        log.write_line("    - Lower load during off-peak times")
        log.write_line("    - Randomized call counts per batch")
        log.write_line("    - Continues running after exiting the UI")
        log.write_line("")

        if not self.selected_profile:
            log.write_line("[!] Warning: No profile selected")
        else:
            log.write_line(f"[+] Profile: {self.selected_profile.metadata.name}")

        if not self.selected_agent_names:
            log.write_line("[!] Warning: No agents selected")
        else:
            log.write_line(f"[+] Selected Agents: {len(self.selected_agent_names)}")

        log.write_line("")
        log.write_line("[*] Configure settings above and click 'Start Daemon'")

    def on_unmount(self) -> None:
        """Cleanup when screen is unmounted."""
        if self.metrics_timer:
            self.metrics_timer.stop()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "btn-refresh-agents":
            self.action_refresh_agents()
        elif button_id == "btn-select-all-agents":
            self.action_select_all_agents()
        elif button_id == "btn-clear-agents":
            self.action_clear_agents()
        elif button_id == "btn-refresh-profiles":
            self._load_profiles()

        # One-time simulation buttons
        if button_id == "btn-onetime-run":
            self.action_run_onetime()
        elif button_id == "btn-onetime-stop":
            self.action_stop_onetime()
        elif button_id == "btn-onetime-export":
            self.action_export_results()

        # Daemon buttons
        elif button_id == "btn-daemon-start":
            self.action_start_daemon()
        elif button_id == "btn-daemon-stop":
            self.action_stop_daemon()

        # Navigation - all back buttons go to home
        elif button_id in ("btn-back-onetime", "btn-back-daemon", "btn-back-results"):
            self.app.pop_screen()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Toggle selection when an agent row is selected."""
        table = event.data_table
        if table.id != "sim-agents-table":
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
        if event.select.id != "sim-profile":
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

    def action_run_current(self) -> None:
        """Run simulation based on current tab."""
        tabs = self.query_one("#sim-tabs", TabbedContent)
        if tabs.active == "tab-onetime":
            self.action_run_onetime()
        elif tabs.active == "tab-daemon":
            self.action_start_daemon()

    def action_stop_current(self) -> None:
        """Stop simulation based on current tab."""
        tabs = self.query_one("#sim-tabs", TabbedContent)
        if tabs.active == "tab-onetime":
            self.action_stop_onetime()
        elif tabs.active == "tab-daemon":
            self.action_stop_daemon()

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

        select = self.query_one("#sim-profile", Select)
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
        else:
            select.clear()

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
        table = self.query_one("#sim-agents-table", DataTable)
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
            self.notify("Select a profile before starting simulations", severity="error")
            log.write_line("[X] No profile selected. Choose one in Simulation Setup.")
            return None
        return self.selected_profile

    # ==================== One-Time Simulation ====================

    def action_run_onetime(self) -> None:
        """Run one-time simulation."""
        if self.simulation_active:
            self.notify("Simulation already running", severity="warning")
            return

        log = self.query_one("#onetime-log", Log)

        # Get configuration
        try:
            num_calls = int(self.query_one("#num-calls", Input).value or "50")
            threads = int(self.query_one("#threads", Input).value or "3")
            delay = float(self.query_one("#delay", Input).value or "0.5")
        except ValueError:
            self.notify("Invalid configuration values", severity="error")
            log.write_line("[X] Invalid configuration. Check Calls, Threads, Delay.")
            return

        # Get simulation type
        sim_type = self.query_one("#sim-type", Select).value

        profile = self._require_profile(log)
        if not profile:
            return

        selected_agents = self._get_selected_agents()
        if not selected_agents:
            self.notify("Select at least one agent to run a simulation", severity="error")
            log.write_line("[X] No agents selected. Choose agents in Simulation Setup.")
            return

        log.write_line("")
        log.write_line("=" * 40)
        log.write_line(f"[>] Starting {sim_type} simulation...")
        log.write_line(f"    Calls: {num_calls}, Threads: {threads}, Delay: {delay}s")
        log.write_line(f"    Profile: {profile.metadata.name}")
        log.write_line(f"    Agents: {len(selected_agents)} selected")
        log.write_line("=" * 40)

        # Create config
        sim_config = SimulationConfig(
            num_calls=num_calls,
            threads=threads,
            delay=delay,
        )

        # Create engine
        query_templates = profile.get_query_templates_dict()
        guardrail_tests = profile.guardrail_tests.get_all_tests()

        self.engine = SimulationEngine(
            agents=selected_agents,
            query_templates=query_templates,
            guardrail_tests=guardrail_tests,
        )

        log.write_line(f"[+] Loaded {len(self.engine.agents)} agents")

        # Run simulation
        self.simulation_active = True
        self._run_onetime_simulation(sim_type, sim_config)

    @work(thread=True, exclusive=True)
    def _run_onetime_simulation(self, sim_type: str, sim_config: SimulationConfig) -> None:
        """Run one-time simulation in background thread."""
        def progress_callback(current, total, message):
            self.app.call_from_thread(self._update_onetime_progress, current, total, message)

        def log_msg(msg):
            self.app.call_from_thread(self._log_onetime, msg)

        try:
            if sim_type == "operations":
                log_msg("[>] Running operations simulation...")
                summary = self.engine.run_operations(sim_config, progress_callback)
                self.engine.save_results()
                get_state_manager().set_operation_summary(summary)
                log_msg(f"[+] Complete! Success rate: {summary.get('success_rate', 0):.1f}%")

            elif sim_type == "guardrails":
                log_msg("[>] Running guardrails simulation...")
                summary = self.engine.run_guardrails(sim_config, progress_callback=progress_callback)
                self.engine.save_results()
                get_state_manager().set_guardrail_summary(summary)
                log_msg(f"[+] Complete! Block rate: {summary.get('overall_block_rate', 0):.1f}%")

            else:  # both
                log_msg("[>] Running operations...")
                ops_summary = self.engine.run_operations(sim_config, progress_callback)
                get_state_manager().set_operation_summary(ops_summary)
                log_msg(f"[+] Operations: {ops_summary.get('success_rate', 0):.1f}% success")

                self.engine.clear_metrics()

                log_msg("[>] Running guardrails...")
                guard_summary = self.engine.run_guardrails(sim_config, progress_callback=progress_callback)
                get_state_manager().set_guardrail_summary(guard_summary)
                log_msg(f"[+] Guardrails: {guard_summary.get('overall_block_rate', 0):.1f}% blocked")

                self.engine.save_results()

            log_msg("")
            log_msg("[*] Simulation completed! View results in 'Results' tab.")
            self.app.call_from_thread(self.notify, "Simulation completed!")
            self.app.call_from_thread(self._load_results)

        except Exception as e:
            import traceback
            log_msg(f"[X] Error: {e}")
            log_msg(f"[X] {traceback.format_exc()[:300]}")
            self.app.call_from_thread(self.notify, f"Error: {e}", severity="error")

        finally:
            self.simulation_active = False
            self.app.call_from_thread(self._update_onetime_progress, 100, 100, "Completed")

    def _log_onetime(self, msg: str) -> None:
        """Write to one-time simulation log."""
        self.query_one("#onetime-log", Log).write_line(msg)

    def _update_onetime_progress(self, current: int, total: int, message: str) -> None:
        """Update one-time simulation progress."""
        self.query_one("#onetime-progress", ProgressBar).update(total=total, progress=current)
        self.query_one("#onetime-status", Static).update(message)

    def action_stop_onetime(self) -> None:
        """Stop the one-time simulation."""
        if self.engine and self.simulation_active:
            self.engine.stop()
            self.simulation_active = False
            self.engine = None
            self._log_onetime("[!] Simulation stopped by user")
            self.notify("Simulation stopped")
            self._update_onetime_progress(0, 100, "Stopped")
        else:
            self.notify("No simulation running", severity="warning")

    # ==================== Daemon Simulation ====================

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
        traffic_rate = self.query_one("#daemon-traffic-rate", Select).value or "medium"
        test_type = self.query_one("#daemon-test-type", Select).value or "both"
        variance_value = self.query_one("#daemon-traffic-variance", Select).value or "20"

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
        log.write_line("=" * 40)
        log.write_line("[>] Starting daemon simulation...")
        log.write_line(f"    Traffic: {traffic_config['label']}")
        log.write_line(f"    Test Type: {test_config['label']}")
        log.write_line(f"    Variance: +/-{variance_pct}%")
        log.write_line(f"    Profile: {profile.metadata.name}")
        log.write_line(f"    Agents: {len(selected_agents)} selected")
        log.write_line("=" * 40)

        # Convert base calls to bounded randomness.
        def apply_variance(base: int, pct: int) -> tuple[int, int]:
            pct = max(0, min(90, int(pct)))
            lo = max(1, int(base * (100 - pct) / 100))
            hi = max(lo, int(base * (100 + pct) / 100))
            return lo, hi

        base_calls = calls_max
        calls_min, calls_max = apply_variance(base_calls, variance_pct)

        # Create config
        daemon_config = DaemonConfig(
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
            daemon_config,
            selected_agents,
            self.selected_profile_id,
            profile.metadata.name,
        )
        if ok:
            self._update_daemon_status(True)
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
            self._update_daemon_status(False)
            get_state_manager().stop_daemon()
            metrics = self.daemon_service.read_metrics()
            if metrics:
                self._update_daemon_metrics(metrics)
            log.write_line("[+] Daemon stopped")
            log.write_line("=" * 40)
            if metrics:
                log.write_line(
                    f"Final: {metrics.get('total_calls', 0)} calls, "
                    f"{metrics.get('success_rate', 0):.1f}% success, "
                    f"Runtime: {metrics.get('runtime', '0s')}"
                )
            log.write_line("=" * 40)
            self.notify("Daemon stopped")
        else:
            self.notify(message, severity="error")
            log.write_line(f"[X] {message}")

    def _update_daemon_status(self, is_running: bool) -> None:
        """Update daemon status display."""
        status = self.query_one("#daemon-status", Static)
        if is_running:
            status.update("RUNNING")
            status.remove_class("status-stopped")
            status.add_class("status-running")
        else:
            status.update("STOPPED")
            status.remove_class("status-running")
            status.add_class("status-stopped")

    def _refresh_daemon_metrics(self) -> None:
        """Refresh daemon metrics periodically."""
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
                self._update_daemon_metrics(metrics)
                get_state_manager().update_daemon_metrics(metrics)
            if not self._daemon_running:
                self._update_daemon_status(True)
                self._daemon_running = True
                get_state_manager().start_daemon()
        elif self._daemon_running:
            self._daemon_running = False
            self._update_daemon_status(False)
            get_state_manager().stop_daemon()

    def _update_daemon_metrics(self, metrics: dict) -> None:
        """Update daemon metrics display."""
        self._update_requests_dashboard(metrics)
        self.query_one("#metric-total-calls", Static).update(str(metrics.get("total_calls", 0)))
        self.query_one("#metric-target-calls-per-min", Static).update(f"{metrics.get('target_calls_per_minute', 0):.1f}")
        self.query_one("#metric-success-rate", Static).update(f"{metrics.get('success_rate', 0):.1f}%")
        self.query_one("#metric-latency", Static).update(f"{metrics.get('avg_latency_ms', 0):.0f}ms")
        self.query_one("#metric-p95-latency", Static).update(f"{metrics.get('p95_latency_ms', 0):.0f}ms")
        self.query_one("#metric-calls-per-min", Static).update(f"{metrics.get('calls_per_minute', 0):.1f}")
        self.query_one("#metric-started-calls-per-min", Static).update(f"{metrics.get('started_calls_per_minute', 0):.1f}")
        self.query_one("#metric-inflight", Static).update(str(metrics.get("inflight_calls", 0)))
        self.query_one("#metric-queue-depth", Static).update(str(metrics.get("queue_depth", 0)))
        self.query_one("#metric-dropped-calls", Static).update(str(metrics.get("dropped_calls", 0)))
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

    # ==================== Results ====================

    def _setup_results_tables(self) -> None:
        """Setup results tables."""
        self.query_one("#ops-types-table", DataTable).add_columns("Agent Type", "Calls", "Percentage")
        self.query_one("#ops-models-table", DataTable).add_columns("Model", "Calls", "Percentage")
        self.query_one("#guard-categories-table", DataTable).add_columns("Category", "Total", "Blocked", "Block Rate", "Status")
        self.query_one("#guard-models-table", DataTable).add_columns("Model", "Total", "Blocked", "Block Rate")

    def _load_results(self) -> None:
        """Load results from state."""
        state = get_state()
        self._load_operations_results(state.operation_summary)
        self._load_guardrails_results(state.guardrail_summary)

    def _load_operations_results(self, summary: dict) -> None:
        """Load operations results."""
        ops_summary = self.query_one("#ops-summary", Static)

        if not summary:
            ops_summary.update("No operations results. Run a simulation first.")
            return

        total = summary.get("total_calls", 0)
        success_rate = summary.get("success_rate", 0)
        avg_latency = summary.get("avg_latency_ms", 0)

        ops_summary.update(
            f"Total Calls: {total} | "
            f"Success: {summary.get('successful_calls', 0)} ({success_rate:.1f}%) | "
            f"Failed: {summary.get('failed_calls', 0)} | "
            f"Avg Latency: {avg_latency:.1f}ms"
        )

        # Update tables
        types_table = self.query_one("#ops-types-table", DataTable)
        types_table.clear()
        for agent_type, count in sorted(summary.get("agent_type_distribution", {}).items(), key=lambda x: x[1], reverse=True):
            pct = count / total * 100 if total > 0 else 0
            types_table.add_row(agent_type, str(count), f"{pct:.1f}%")

        models_table = self.query_one("#ops-models-table", DataTable)
        models_table.clear()
        for model, count in sorted(summary.get("model_distribution", {}).items(), key=lambda x: x[1], reverse=True):
            pct = count / total * 100 if total > 0 else 0
            models_table.add_row(model, str(count), f"{pct:.1f}%")

    def _load_guardrails_results(self, summary: dict) -> None:
        """Load guardrails results."""
        guard_summary = self.query_one("#guard-summary", Static)

        if not summary:
            guard_summary.update("No guardrails results. Run a simulation first.")
            return

        total = summary.get("total_tests", 0)
        block_rate = summary.get("overall_block_rate", 0)
        recommendation = summary.get("recommendation", "N/A")

        guard_summary.update(
            f"Total Tests: {total} | "
            f"Blocked: {summary.get('blocked', 0)} ({block_rate:.1f}%) | "
            f"Allowed: {summary.get('allowed', 0)} | "
            f"Recommendation: {recommendation}"
        )

        # Update tables
        cats_table = self.query_one("#guard-categories-table", DataTable)
        cats_table.clear()
        for cat, stats in sorted(summary.get("category_stats", {}).items(), key=lambda x: x[1].get("block_rate", 0)):
            cat_rate = stats.get("block_rate", 0)
            status = "OK" if cat_rate >= 95 else "WARN" if cat_rate >= 80 else "CRITICAL"
            cats_table.add_row(cat, str(stats.get("total", 0)), str(stats.get("blocked", 0)), f"{cat_rate:.1f}%", status)

        models_table = self.query_one("#guard-models-table", DataTable)
        models_table.clear()
        for model, stats in sorted(summary.get("model_stats", {}).items(), key=lambda x: x[1].get("block_rate", 0)):
            models_table.add_row(model, str(stats.get("total", 0)), str(stats.get("blocked", 0)), f"{stats.get('block_rate', 0):.1f}%")

    def action_export_results(self) -> None:
        """Export results to files."""
        state = get_state()

        if state.operation_summary:
            self.notify(f"Operations saved to {config.SIMULATION_SUMMARY_JSON}")
        if state.guardrail_summary:
            self.notify(f"Guardrails saved to {config.GUARDRAILS_SUMMARY_JSON}")
        if not state.operation_summary and not state.guardrail_summary:
            self.notify("No results to export", severity="warning")
