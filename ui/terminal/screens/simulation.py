"""
Simulation screen for the Textual TUI application.

Allows users to run simulations and monitor progress.
Supports both one-time simulations and long-running daemon simulations.
"""

import os
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Button, Input, ProgressBar, Log, Select, DataTable, TabbedContent, TabPane, Label
from textual.containers import Vertical, Horizontal, VerticalScroll, Grid
from textual import work
from textual.timer import Timer

from ui.shared.state_manager import get_state_manager, get_state
from src.core.simulation_engine import SimulationEngine, SimulationConfig
from src.core.daemon_runner import DaemonRunner, DaemonConfig
from src.core import config


class SimulationScreen(Screen):
    """Screen for running simulations."""

    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("r", "run_current", "Run"),
        ("x", "stop_current", "Stop"),
    ]

    DEFAULT_CSS = """
    SimulationScreen {
        layout: vertical;
        padding: 0 1;
    }

    /* Common styles */
    .config-section {
        height: auto;
        padding: 1;
        margin-bottom: 1;
        border: solid $secondary;
        background: $surface-darken-1;
    }

    .config-section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }

    .config-row {
        height: auto;
        margin-bottom: 1;
    }

    .config-row:last-of-type {
        margin-bottom: 0;
    }

    .input-label {
        width: 14;
        padding-right: 1;
    }

    .input-field {
        width: 12;
    }

    .button-row {
        height: auto;
        padding: 1 0;
        align: center middle;
    }

    .button-row Button {
        margin: 0 1;
    }

    /* One-time simulation tab */
    #onetime-config {
        height: auto;
        margin-bottom: 1;
    }

    #onetime-type-section {
        height: auto;
        padding: 1;
        margin-bottom: 1;
        border: solid $accent;
        background: $surface-darken-1;
    }

    #sim-type {
        width: 100%;
        margin-top: 1;
    }

    #onetime-progress-section {
        height: auto;
        padding: 1;
        margin-bottom: 1;
        border: solid $primary;
        background: $surface-darken-1;
    }

    #onetime-log-section {
        height: 1fr;
        min-height: 8;
    }

    #onetime-log {
        height: 1fr;
        border: solid $primary;
        background: $surface-darken-1;
    }

    /* Daemon simulation tab */
    #daemon-config {
        height: auto;
        margin-bottom: 1;
    }

    #daemon-status-section {
        height: auto;
        padding: 1;
        margin-bottom: 1;
        border: solid $accent;
        background: $surface-darken-1;
    }

    #daemon-status {
        text-style: bold;
        text-align: center;
    }

    .status-running {
        color: $success;
    }

    .status-stopped {
        color: $error;
    }

    #daemon-metrics-section {
        height: auto;
        padding: 1;
        margin-bottom: 1;
        border: solid $primary;
        background: $surface-darken-1;
    }

    #metrics-grid {
        grid-size: 3;
        grid-columns: 1fr 1fr 1fr;
        grid-gutter: 1;
        height: auto;
    }

    .metric-box {
        padding: 1;
        border: tall $secondary;
        background: $surface;
        height: auto;
        align: center middle;
        text-align: center;
    }

    .metric-header {
        color: $text-muted;
        text-style: bold;
    }

    .metric-value {
        color: $accent;
        text-style: bold;
    }

    #daemon-log-section {
        height: 1fr;
        min-height: 8;
    }

    #daemon-log {
        height: 1fr;
        border: solid $primary;
        background: $surface-darken-1;
    }

    /* Results tab */
    .results-section {
        margin-bottom: 1;
        padding: 1;
        border: solid $secondary;
        background: $surface-darken-1;
    }

    .results-header {
        text-align: center;
        background: $primary;
        color: $text;
        text-style: bold;
        padding: 0 1;
        margin-bottom: 1;
    }

    .summary-text {
        padding: 1;
        margin-bottom: 1;
    }

    .table-container {
        height: auto;
    }

    .table-box {
        width: 1fr;
        margin: 0 1;
    }

    .table-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
        text-align: center;
    }
    """

    def __init__(self):
        super().__init__()
        self.engine = None
        self.simulation_active = False
        self.daemon: DaemonRunner = None
        self.metrics_timer: Timer = None

    def action_go_back(self) -> None:
        """Go back to previous screen."""
        self.app.pop_screen()

    def compose(self) -> ComposeResult:
        yield Static("Simulation Dashboard", id="title", classes="screen-title")

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

                # Progress
                with Vertical(id="onetime-progress-section"):
                    yield Static("Progress", classes="config-section-title")
                    yield ProgressBar(id="onetime-progress", total=100, show_eta=True)
                    yield Static("Ready to run simulation", id="onetime-status")

                # Log
                with Vertical(id="onetime-log-section"):
                    yield Static("Execution Log", classes="config-section-title")
                    yield Log(id="onetime-log", auto_scroll=True)

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
                        yield Static("Interval (sec):", classes="input-label")
                        yield Input(value="60", id="daemon-interval", type="integer", classes="input-field")
                        yield Static("Time between batches", classes="description")
                    with Horizontal(classes="config-row"):
                        yield Static("Min Calls:", classes="input-label")
                        yield Input(value="5", id="daemon-calls-min", type="integer", classes="input-field")
                        yield Static("Minimum calls per batch", classes="description")
                    with Horizontal(classes="config-row"):
                        yield Static("Max Calls:", classes="input-label")
                        yield Input(value="15", id="daemon-calls-max", type="integer", classes="input-field")
                        yield Static("Maximum calls per batch", classes="description")
                    with Horizontal(classes="config-row"):
                        yield Static("Threads:", classes="input-label")
                        yield Input(value="3", id="daemon-threads", type="integer", classes="input-field")
                        yield Static("Concurrent threads", classes="description")
                    with Horizontal(classes="config-row"):
                        yield Static("Delay (sec):", classes="input-label")
                        yield Input(value="0.5", id="daemon-delay", classes="input-field")
                        yield Static("Delay between calls", classes="description")
                    with Horizontal(classes="config-row"):
                        yield Static("Ops Weight %:", classes="input-label")
                        yield Input(value="80", id="daemon-ops-weight", type="integer", classes="input-field")
                        yield Static("Operations vs Guardrails ratio", classes="description")

                # Buttons
                with Horizontal(classes="button-row"):
                    yield Button("Start Daemon", id="btn-daemon-start", variant="primary")
                    yield Button("Stop Daemon", id="btn-daemon-stop", variant="error")

                # Real-time Metrics
                with Vertical(id="daemon-metrics-section"):
                    yield Static("Real-time Metrics", classes="config-section-title")
                    with Grid(id="metrics-grid"):
                        with Vertical(classes="metric-box"):
                            yield Static("Total Calls", classes="metric-header")
                            yield Static("0", id="metric-total-calls", classes="metric-value")
                        with Vertical(classes="metric-box"):
                            yield Static("Success Rate", classes="metric-header")
                            yield Static("0%", id="metric-success-rate", classes="metric-value")
                        with Vertical(classes="metric-box"):
                            yield Static("Avg Latency", classes="metric-header")
                            yield Static("0ms", id="metric-latency", classes="metric-value")
                        with Vertical(classes="metric-box"):
                            yield Static("Calls/min", classes="metric-header")
                            yield Static("0", id="metric-calls-per-min", classes="metric-value")
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
                            yield Static("Load Profile", classes="metric-header")
                            yield Static("normal", id="metric-load-profile", classes="metric-value")

                # Log
                with Vertical(id="daemon-log-section"):
                    yield Static("Daemon Log", classes="config-section-title")
                    yield Log(id="daemon-log", auto_scroll=True)

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

    def on_mount(self) -> None:
        """Initialize the screen."""
        self._init_onetime_log()
        self._init_daemon_log()
        self._setup_results_tables()
        self._load_results()
        # Start metrics refresh timer
        self.metrics_timer = self.set_interval(1.0, self._refresh_daemon_metrics)

    def _init_onetime_log(self) -> None:
        """Initialize the one-time simulation log."""
        state = get_state()
        log = self.query_one("#onetime-log", Log)

        log.write_line("[*] One-Time Simulation")
        log.write_line("=" * 40)

        if not state.current_profile:
            log.write_line("[!] Warning: No industry profile selected")
        else:
            log.write_line(f"[+] Profile: {state.current_profile.metadata.name}")

        if not state.created_agents:
            log.write_line("[!] Warning: No agents created in session")
        else:
            log.write_line(f"[+] Session Agents: {len(state.created_agents)}")

        log.write_line("")
        log.write_line("[*] Configure settings above and click 'Start Simulation'")

    def _init_daemon_log(self) -> None:
        """Initialize the daemon simulation log."""
        state = get_state()
        log = self.query_one("#daemon-log", Log)

        log.write_line("[*] Long-Running Daemon Simulation")
        log.write_line("=" * 40)
        log.write_line("[*] Simulates production traffic patterns:")
        log.write_line("    - Higher load during business hours")
        log.write_line("    - Lower load during off-peak times")
        log.write_line("    - Randomized call counts per batch")
        log.write_line("")

        if not state.current_profile:
            log.write_line("[!] Warning: No industry profile selected")
        else:
            log.write_line(f"[+] Profile: {state.current_profile.metadata.name}")

        log.write_line("")
        log.write_line("[*] Configure settings above and click 'Start Daemon'")

    def on_unmount(self) -> None:
        """Cleanup when screen is unmounted."""
        if self.metrics_timer:
            self.metrics_timer.stop()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

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

    # ==================== One-Time Simulation ====================

    def action_run_onetime(self) -> None:
        """Run one-time simulation."""
        if self.simulation_active:
            self.notify("Simulation already running", severity="warning")
            return

        state = get_state()
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

        # Check agents CSV
        agents_csv = state.agents_csv_path
        if not os.path.exists(agents_csv):
            self.notify("Agents CSV not found. Create agents first.", severity="error")
            log.write_line(f"[X] Agents CSV not found: {agents_csv}")
            return

        log.write_line("")
        log.write_line("=" * 40)
        log.write_line(f"[>] Starting {sim_type} simulation...")
        log.write_line(f"    Calls: {num_calls}, Threads: {threads}, Delay: {delay}s")
        log.write_line("=" * 40)

        # Create config
        sim_config = SimulationConfig(
            num_calls=num_calls,
            threads=threads,
            delay=delay,
        )

        # Create engine
        query_templates = state.current_profile.get_query_templates_dict() if state.current_profile else {}
        guardrail_tests = state.current_profile.guardrail_tests.get_all_tests() if state.current_profile else {}

        self.engine = SimulationEngine(
            agents_csv=agents_csv,
            query_templates=query_templates,
            guardrail_tests=guardrail_tests,
        )

        if len(self.engine.agents) == 0:
            self.notify("No agents found in CSV", severity="error")
            log.write_line("[X] No agents found in CSV file")
            return

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

    def action_start_daemon(self) -> None:
        """Start the daemon simulation."""
        if self.daemon and self.daemon.is_running:
            self.notify("Daemon is already running", severity="warning")
            return

        state = get_state()
        log = self.query_one("#daemon-log", Log)

        # Get configuration
        try:
            interval = int(self.query_one("#daemon-interval", Input).value or "60")
            calls_min = int(self.query_one("#daemon-calls-min", Input).value or "5")
            calls_max = int(self.query_one("#daemon-calls-max", Input).value or "15")
            threads = int(self.query_one("#daemon-threads", Input).value or "3")
            delay = float(self.query_one("#daemon-delay", Input).value or "0.5")
            ops_weight = int(self.query_one("#daemon-ops-weight", Input).value or "80")
        except ValueError:
            self.notify("Invalid configuration values", severity="error")
            log.write_line("[X] Invalid configuration values")
            return

        # Check agents CSV
        agents_csv = state.agents_csv_path
        if not os.path.exists(agents_csv):
            self.notify("Agents CSV not found. Create agents first.", severity="error")
            log.write_line(f"[X] Agents CSV not found: {agents_csv}")
            return

        log.write_line("")
        log.write_line("=" * 40)
        log.write_line("[>] Starting daemon simulation...")
        log.write_line(f"    Interval: {interval}s, Calls: {calls_min}-{calls_max}")
        log.write_line(f"    Threads: {threads}, Ops weight: {ops_weight}%")
        log.write_line("=" * 40)

        # Create config
        daemon_config = DaemonConfig(
            interval_seconds=interval,
            calls_per_batch_min=calls_min,
            calls_per_batch_max=calls_max,
            threads=threads,
            delay=delay,
            operations_weight=ops_weight,
        )

        # Create daemon
        self.daemon = DaemonRunner(
            agents_csv=agents_csv,
            profile=state.current_profile,
        )

        if self.daemon.get_agent_count() == 0:
            self.notify("No agents found in CSV", severity="error")
            log.write_line("[X] No agents found in CSV file")
            return

        log.write_line(f"[+] Loaded {self.daemon.get_agent_count()} agents")

        # Callbacks
        def log_callback(message: str):
            self.app.call_from_thread(self._log_daemon, message)

        def metrics_callback(metrics: dict):
            self.app.call_from_thread(self._update_daemon_metrics, metrics)

        # Start
        if self.daemon.start(daemon_config, log_callback=log_callback, metrics_callback=metrics_callback):
            self._update_daemon_status(True)
            get_state_manager().start_daemon()
            self.notify("Daemon started")
            log.write_line("[+] Daemon started successfully")
        else:
            self.notify("Failed to start daemon", severity="error")
            log.write_line("[X] Failed to start daemon")

    def action_stop_daemon(self) -> None:
        """Stop the daemon simulation."""
        if not self.daemon or not self.daemon.is_running:
            self.notify("Daemon is not running", severity="warning")
            return

        log = self.query_one("#daemon-log", Log)
        log.write_line("")
        log.write_line("[>] Stopping daemon...")

        self.daemon.stop()
        self._update_daemon_status(False)
        get_state_manager().stop_daemon()

        # Final stats
        metrics = self.daemon.get_metrics()
        log.write_line("[+] Daemon stopped")
        log.write_line("=" * 40)
        log.write_line(f"Final: {metrics.get('total_calls', 0)} calls, "
                      f"{metrics.get('success_rate', 0):.1f}% success, "
                      f"Runtime: {metrics.get('runtime', '0s')}")
        log.write_line("=" * 40)

        self.notify("Daemon stopped")

    def _log_daemon(self, msg: str) -> None:
        """Write to daemon log."""
        self.query_one("#daemon-log", Log).write_line(msg)

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
        if self.daemon and self.daemon.is_running:
            metrics = self.daemon.get_metrics()
            self._update_daemon_metrics(metrics)
            get_state_manager().update_daemon_metrics(metrics)

    def _update_daemon_metrics(self, metrics: dict) -> None:
        """Update daemon metrics display."""
        self.query_one("#metric-total-calls", Static).update(str(metrics.get("total_calls", 0)))
        self.query_one("#metric-success-rate", Static).update(f"{metrics.get('success_rate', 0):.1f}%")
        self.query_one("#metric-latency", Static).update(f"{metrics.get('avg_latency_ms', 0):.0f}ms")
        self.query_one("#metric-calls-per-min", Static).update(f"{metrics.get('calls_per_minute', 0):.1f}")
        self.query_one("#metric-operations", Static).update(str(metrics.get("total_operations", 0)))
        self.query_one("#metric-guardrails", Static).update(str(metrics.get("total_guardrails", 0)))
        self.query_one("#metric-batches", Static).update(str(metrics.get("batches_completed", 0)))
        self.query_one("#metric-runtime", Static).update(metrics.get("runtime", "0s"))
        self.query_one("#metric-load-profile", Static).update(metrics.get("current_load_profile", "normal"))

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
