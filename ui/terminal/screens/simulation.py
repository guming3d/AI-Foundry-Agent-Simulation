"""
Simulation screen for the Textual TUI application.

Allows users to run simulations and monitor progress.
Supports both one-time simulations and long-running daemon simulations.
"""

import os
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Button, Input, ProgressBar, Log, Select, RadioSet, RadioButton
from textual.containers import Vertical, Horizontal
from textual import work
from textual.timer import Timer

from ui.shared.state_manager import get_state_manager, get_state
from src.core.simulation_engine import SimulationEngine, SimulationConfig
from src.core.daemon_runner import DaemonRunner, DaemonConfig


class SimulationScreen(Screen):
    """Screen for running simulations."""

    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("r", "run_simulation", "Run"),
        ("x", "stop_simulation", "Stop"),
    ]

    DEFAULT_CSS = """
    SimulationScreen {
        layout: vertical;
        padding: 0 1;
    }

    #mode-panel {
        margin: 0 0 1 0;
        padding: 1;
        border: solid $accent;
        background: $surface-darken-1;
    }

    #mode-selector {
        margin: 0;
    }

    #config-row-onetime, #config-row-daemon {
        height: auto;
        max-height: 6;
        padding: 0;
        margin-bottom: 1;
    }

    #type-panel {
        width: 1fr;
        height: auto;
        padding: 1;
        border: solid $secondary;
        background: $surface-darken-1;
    }

    #config-panel-onetime, #daemon-config-1, #daemon-config-2 {
        width: 2fr;
        height: auto;
        padding: 1;
        margin-left: 1;
        border: solid $secondary;
        background: $surface-darken-1;
    }

    #daemon-config-1 {
        width: 1fr;
        margin-left: 0;
    }

    #config-panel-onetime Horizontal,
    #daemon-config-1 Horizontal,
    #daemon-config-2 Horizontal {
        height: auto;
        margin: 0;
    }

    #config-panel-onetime Input,
    #daemon-config-1 Input,
    #daemon-config-2 Input {
        width: 10;
    }

    .input-label {
        width: 12;
        padding-right: 1;
    }

    .metric-label {
        width: 14;
        text-style: bold;
    }

    .metric-value {
        width: 10;
    }

    #daemon-metrics-panel {
        margin: 0 0 1 0;
        padding: 1;
        border: solid $primary;
        background: $surface-darken-1;
    }

    #daemon-status {
        text-style: bold;
        padding: 0 0 1 0;
    }

    .status-running {
        color: $success;
    }

    .status-stopped {
        color: $error;
    }

    #metrics-grid {
        height: auto;
    }

    #progress-panel {
        margin: 0 0 1 0;
        padding: 1;
        border: solid $primary;
        background: $surface-darken-1;
    }

    #log-panel {
        height: 1fr;
        min-height: 10;
        padding: 0;
    }

    #sim-log {
        height: 1fr;
        border: solid $primary;
        background: $surface-darken-1;
        margin: 0;
    }

    #sim-type {
        width: 100%;
    }

    .hidden {
        display: none;
    }
    """

    def __init__(self):
        super().__init__()
        self.engine = None
        self.simulation_active = False
        self.simulation_mode = "onetime"  # "onetime" or "daemon"
        self.daemon: DaemonRunner = None
        self.metrics_timer: Timer = None

    def action_go_back(self) -> None:
        """Go back to previous screen."""
        self.app.pop_screen()

    def compose(self) -> ComposeResult:
        # Header with title
        yield Static("Simulation Dashboard", id="title", classes="screen-title")
        yield Static("Run one-time simulations or long-running production traffic simulation", classes="description")

        # Simulation Mode Selection
        yield Vertical(
            Static("Simulation Mode:", classes="section-title"),
            RadioSet(
                RadioButton("One-Time Simulation", id="mode-onetime", value=True),
                RadioButton("Long-Running Daemon", id="mode-daemon"),
                id="mode-selector",
            ),
            id="mode-panel",
        )

        # Button bar
        yield Horizontal(
            Button("Run [R]", id="btn-run", variant="primary"),
            Button("Stop [X]", id="btn-stop", variant="error"),
            Button("Back [Esc]", id="btn-back"),
            id="button-bar",
        )

        # One-Time Simulation Config
        yield Horizontal(
            Vertical(
                Static("Type:", classes="label"),
                Select(
                    [
                        ("Operations", "operations"),
                        ("Guardrails", "guardrails"),
                        ("Both", "both"),
                    ],
                    value="operations",
                    id="sim-type",
                    allow_blank=False,
                ),
                id="type-panel",
            ),
            Vertical(
                Horizontal(
                    Static("Calls:", classes="input-label"),
                    Input(value="50", id="num-calls", type="integer"),
                ),
                Horizontal(
                    Static("Threads:", classes="input-label"),
                    Input(value="3", id="threads", type="integer"),
                ),
                Horizontal(
                    Static("Delay:", classes="input-label"),
                    Input(value="0.5", id="delay"),
                ),
                id="config-panel-onetime",
            ),
            id="config-row-onetime",
        )

        # Daemon Config
        yield Horizontal(
            Vertical(
                Horizontal(
                    Static("Interval (s):", classes="input-label"),
                    Input(value="60", id="daemon-interval", type="integer"),
                ),
                Horizontal(
                    Static("Min Calls:", classes="input-label"),
                    Input(value="5", id="daemon-calls-min", type="integer"),
                ),
                Horizontal(
                    Static("Max Calls:", classes="input-label"),
                    Input(value="15", id="daemon-calls-max", type="integer"),
                ),
                id="daemon-config-1",
            ),
            Vertical(
                Horizontal(
                    Static("Threads:", classes="input-label"),
                    Input(value="3", id="daemon-threads", type="integer"),
                ),
                Horizontal(
                    Static("Delay (s):", classes="input-label"),
                    Input(value="0.5", id="daemon-delay"),
                ),
                Horizontal(
                    Static("Ops Weight %:", classes="input-label"),
                    Input(value="80", id="daemon-ops-weight", type="integer"),
                ),
                id="daemon-config-2",
            ),
            id="config-row-daemon",
            classes="hidden",
        )

        # Daemon Metrics Panel
        yield Vertical(
            Static(id="daemon-status", classes="info-text"),
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
                        Static("Load Profile:", classes="metric-label"),
                        Static("normal", id="metric-load-profile", classes="metric-value"),
                    ),
                ),
                id="metrics-grid",
            ),
            id="daemon-metrics-panel",
            classes="hidden",
        )

        # Progress section (for one-time)
        yield Vertical(
            ProgressBar(id="progress-bar", total=100, show_eta=True),
            Static("Ready", id="progress-status", classes="info-text"),
            id="progress-panel",
        )

        # Log section
        yield Vertical(
            Static("Log:", classes="section-title"),
            Log(id="sim-log", auto_scroll=True),
            id="log-panel",
        )

    def on_mount(self) -> None:
        """Initialize the screen."""
        self._check_prerequisites()
        self._update_daemon_status(False)
        # Start metrics refresh timer
        self.metrics_timer = self.set_interval(1.0, self._refresh_daemon_metrics)

    def on_unmount(self) -> None:
        """Cleanup when screen is unmounted."""
        if self.metrics_timer:
            self.metrics_timer.stop()

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        """Handle mode selection change."""
        if event.pressed.id == "mode-onetime":
            self.simulation_mode = "onetime"
            self._switch_to_onetime_mode()
        elif event.pressed.id == "mode-daemon":
            self.simulation_mode = "daemon"
            self._switch_to_daemon_mode()

    def _switch_to_onetime_mode(self) -> None:
        """Switch UI to one-time simulation mode."""
        # Show one-time controls
        self.query_one("#config-row-onetime").remove_class("hidden")
        self.query_one("#progress-panel").remove_class("hidden")

        # Hide daemon controls
        self.query_one("#config-row-daemon").add_class("hidden")
        self.query_one("#daemon-metrics-panel").add_class("hidden")

        log = self.query_one("#sim-log", Log)
        log.write_line("")
        log.write_line("[*] Switched to One-Time Simulation mode")

    def _switch_to_daemon_mode(self) -> None:
        """Switch UI to daemon simulation mode."""
        # Hide one-time controls
        self.query_one("#config-row-onetime").add_class("hidden")
        self.query_one("#progress-panel").add_class("hidden")

        # Show daemon controls
        self.query_one("#config-row-daemon").remove_class("hidden")
        self.query_one("#daemon-metrics-panel").remove_class("hidden")

        log = self.query_one("#sim-log", Log)
        log.write_line("")
        log.write_line("[*] Switched to Long-Running Daemon mode")
        log.write_line("[*] Daemon simulates production traffic based on time of day")
        log.write_line("[*] Higher load during busy hours, lower during off-peak")

    def _check_prerequisites(self) -> None:
        """Check if prerequisites are met for simulation."""
        state = get_state()
        log = self.query_one("#sim-log", Log)

        if not state.current_profile:
            log.write_line("[!] Warning: No industry profile selected")
        else:
            log.write_line(f"[+] Profile: {state.current_profile.metadata.name}")

        if not state.created_agents:
            log.write_line("[!] Warning: No agents created. Using existing CSV if available.")
        else:
            log.write_line(f"[+] Agents: {len(state.created_agents)} available")

        log.write_line("[*] Ready to run simulation. Press [R] or click Run.")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "btn-run":
            if self.simulation_mode == "onetime":
                self.action_run_simulation()
            else:
                self.action_start_daemon()
        elif button_id == "btn-stop":
            if self.simulation_mode == "onetime":
                self.action_stop_simulation()
            else:
                self.action_stop_daemon()
        elif button_id == "btn-back":
            self.app.pop_screen()

    def action_run_simulation(self) -> None:
        """Run one-time simulation."""
        import os

        if self.simulation_active:
            self.notify("Simulation already running", severity="warning")
            return

        state = get_state()
        log = self.query_one("#sim-log", Log)

        # Get configuration
        try:
            num_calls = int(self.query_one("#num-calls", Input).value or "50")
            threads = int(self.query_one("#threads", Input).value or "3")
            delay = float(self.query_one("#delay", Input).value or "0.5")
        except ValueError:
            self.notify("Invalid configuration values", severity="error")
            log.write_line("[X] Invalid configuration values. Please check Calls, Threads, and Delay.")
            return

        # Get simulation type from Select widget
        sim_type_widget = self.query_one("#sim-type", Select)
        sim_type = sim_type_widget.value

        agents_csv = state.agents_csv_path
        if not os.path.exists(agents_csv):
            self.notify("Agents CSV not found. Please create agents first.", severity="error")
            log.write_line(f"[X] Agents CSV not found: {agents_csv}")
            return

        log.write_line("")
        log.write_line("=" * 50)
        log.write_line(f"[>] Starting {sim_type} simulation...")
        log.write_line(f"    Total calls: {num_calls}")
        log.write_line(f"    Threads: {threads}, Delay: {delay}s")
        log.write_line("=" * 50)

        # Create config
        config = SimulationConfig(
            total_calls=num_calls,
            threads=threads,
            delay=delay,
            run_operations=(sim_type in ["operations", "both"]),
            run_guardrails=(sim_type in ["guardrails", "both"]),
        )

        # Create engine
        self.engine = SimulationEngine(
            agents_csv=agents_csv,
            profile=state.current_profile,
        )

        if self.engine.get_agent_count() == 0:
            self.notify("No agents found in CSV", severity="error")
            log.write_line("[X] No agents found in CSV file")
            return

        log.write_line(f"[+] Loaded {self.engine.get_agent_count()} agents")

        # Define callbacks
        def progress_callback(current, total, message):
            self.app.call_from_thread(self._update_progress, current, total, message)

        def log_callback(message):
            self.app.call_from_thread(self._log_message, message)

        # Run simulation in background
        self.simulation_active = True
        self.run_simulation_async(config, progress_callback, log_callback)
    @work(thread=True, exclusive=True)
    def run_simulation_in_thread(self, sim_type: str, config: SimulationConfig) -> None:
        """Run simulation in a background thread (non-blocking)."""
        self.simulation_active = True

        def progress_callback(current, total, message):
            self.app.call_from_thread(self._update_progress, current, total, message)
            # Also log each progress update
            self.app.call_from_thread(self._log_message, f"    [{current}/{total}] {message}")

        def log_message(msg):
            self.app.call_from_thread(self._log_message, msg)

        try:
            log_message(f"[>] Initializing {sim_type} simulation...")
            log_message(f"    Agents loaded: {len(self.engine.agents)}")

            if sim_type == "operations":
                log_message("[>] Running operations simulation...")
                summary = self.engine.run_operations(config, progress_callback)
                log_message("[>] Saving results...")
                self.engine.save_results()
                get_state_manager().set_operation_summary(summary)
                log_message(f"[+] Operations complete!")
                log_message(f"    Total calls: {summary.get('total_calls', 0)}")
                log_message(f"    Success rate: {summary.get('success_rate', 0):.1f}%")
                log_message(f"    Avg latency: {summary.get('avg_latency_ms', 0):.1f}ms")

            elif sim_type == "guardrails":
                log_message("[>] Running guardrails simulation...")
                summary = self.engine.run_guardrails(config, progress_callback=progress_callback)
                log_message("[>] Saving results...")
                self.engine.save_results()
                get_state_manager().set_guardrail_summary(summary)
                log_message(f"[+] Guardrails complete!")
                log_message(f"    Total tests: {summary.get('total_tests', 0)}")
                log_message(f"    Block rate: {summary.get('overall_block_rate', 0):.1f}%")

            else:  # both
                log_message("[>] Running operations simulation...")
                ops_summary = self.engine.run_operations(config, progress_callback)
                get_state_manager().set_operation_summary(ops_summary)
                log_message(f"[+] Operations: {ops_summary.get('success_rate', 0):.1f}% success")

                self.engine.clear_metrics()

                log_message("[>] Running guardrails simulation...")
                guard_summary = self.engine.run_guardrails(config, progress_callback=progress_callback)
                get_state_manager().set_guardrail_summary(guard_summary)
                log_message(f"[+] Guardrails: {guard_summary.get('overall_block_rate', 0):.1f}% blocked")

                log_message("[>] Saving results...")
                self.engine.save_results()

            log_message("")
            log_message("[*] ========================================")
            log_message("[*] Simulation completed successfully!")
            log_message("[*] View results in Results screen (F6)")
            log_message("[*] ========================================")
            self.app.call_from_thread(self.notify, "Simulation completed!")

        except Exception as e:
            import traceback
            log_message(f"[X] Error: {e}")
            log_message(f"[X] Details: {traceback.format_exc()[:500]}")
            self.app.call_from_thread(self.notify, f"Error: {e}", severity="error")

        finally:
            self.simulation_active = False
            self.app.call_from_thread(self._update_progress, 100, 100, "Completed")

    def _log_message(self, msg: str) -> None:
        """Write a message to the log widget."""
        log = self.query_one("#sim-log", Log)
        log.write_line(msg)

    def _update_progress(self, current: int, total: int, message: str) -> None:
        """Update progress display."""
        progress = self.query_one("#progress-bar", ProgressBar)
        status = self.query_one("#progress-status", Static)

        progress.update(total=total, progress=current)
        status.update(message)

    def action_stop_simulation(self) -> None:
        """Stop the current simulation."""
        if self.engine and self.simulation_active:
            self.engine.stop()
            self.simulation_active = False
            self.engine = None
            log = self.query_one("#sim-log", Log)
            log.write_line("[!] Simulation stopped by user")
            self.notify("Simulation stopped")
            self._update_progress(0, 100, "Stopped")
        else:
            self.notify("No simulation running", severity="warning")

    # Daemon simulation methods

    def action_start_daemon(self) -> None:
        """Start the daemon simulation."""
        if self.daemon and self.daemon.is_running:
            self.notify("Daemon is already running", severity="warning")
            return

        state = get_state()
        log = self.query_one("#sim-log", Log)

        # Validate configuration
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
            self.notify("Agents CSV not found. Please create agents first.", severity="error")
            log.write_line(f"[X] Agents CSV not found: {agents_csv}")
            return

        log.write_line("")
        log.write_line("=" * 50)
        log.write_line("[>] Starting long-running daemon simulation...")
        log.write_line(f"    Interval: {interval}s")
        log.write_line(f"    Calls per batch: {calls_min}-{calls_max}")
        log.write_line(f"    Threads: {threads}, Delay: {delay}s")
        log.write_line(f"    Operations weight: {ops_weight}%")
        log.write_line("=" * 50)

        # Create config
        config = DaemonConfig(
            interval_seconds=interval,
            calls_per_batch_min=calls_min,
            calls_per_batch_max=calls_max,
            threads=threads,
            delay=delay,
            operations_weight=ops_weight,
        )

        # Create daemon runner
        self.daemon = DaemonRunner(
            agents_csv=agents_csv,
            profile=state.current_profile,
        )

        if self.daemon.get_agent_count() == 0:
            self.notify("No agents found in CSV", severity="error")
            log.write_line("[X] No agents found in CSV file")
            return

        log.write_line(f"[+] Loaded {self.daemon.get_agent_count()} agents")

        # Define callbacks
        def log_callback(message: str):
            self.app.call_from_thread(self._log_message, message)

        def metrics_callback(metrics: dict):
            self.app.call_from_thread(self._update_daemon_metrics, metrics)

        # Start daemon
        if self.daemon.start(config, log_callback=log_callback, metrics_callback=metrics_callback):
            self._update_daemon_status(True)
            get_state_manager().start_daemon()
            self.notify("Daemon started")
            log.write_line("[+] Daemon started successfully")
            log.write_line("[*] Simulating production traffic based on time of day...")
        else:
            self.notify("Failed to start daemon", severity="error")
            log.write_line("[X] Failed to start daemon")

    def action_stop_daemon(self) -> None:
        """Stop the daemon simulation."""
        if not self.daemon or not self.daemon.is_running:
            self.notify("Daemon is not running", severity="warning")
            return

        log = self.query_one("#sim-log", Log)
        log.write_line("")
        log.write_line("[>] Stopping daemon...")

        self.daemon.stop()
        self._update_daemon_status(False)
        get_state_manager().stop_daemon()

        log.write_line("[+] Daemon stopped")
        log.write_line("=" * 50)

        # Show final metrics
        metrics = self.daemon.get_metrics()
        log.write_line(f"Final Statistics:")
        log.write_line(f"  Total Calls: {metrics.get('total_calls', 0)}")
        log.write_line(f"  Success Rate: {metrics.get('success_rate', 0):.1f}%")
        log.write_line(f"  Avg Latency: {metrics.get('avg_latency_ms', 0):.1f}ms")
        log.write_line(f"  Runtime: {metrics.get('runtime', '0s')}")
        log.write_line("=" * 50)

        self.notify("Daemon stopped")

    def _update_daemon_status(self, is_running: bool) -> None:
        """Update the daemon status indicator."""
        status = self.query_one("#daemon-status", Static)
        if is_running:
            status.update("Status: RUNNING")
            status.remove_class("status-stopped")
            status.add_class("status-running")
        else:
            status.update("Status: STOPPED")
            status.remove_class("status-running")
            status.add_class("status-stopped")

    def _refresh_daemon_metrics(self) -> None:
        """Refresh the daemon metrics display."""
        if self.daemon and self.daemon.is_running:
            metrics = self.daemon.get_metrics()
            self._update_daemon_metrics(metrics)
            get_state_manager().update_daemon_metrics(metrics)

    def _update_daemon_metrics(self, metrics: dict) -> None:
        """Update the daemon metrics display widgets."""
        self.query_one("#metric-total-calls", Static).update(str(metrics.get("total_calls", 0)))
        self.query_one("#metric-success-rate", Static).update(f"{metrics.get('success_rate', 0):.1f}%")
        self.query_one("#metric-latency", Static).update(f"{metrics.get('avg_latency_ms', 0):.0f}ms")
        self.query_one("#metric-calls-per-min", Static).update(f"{metrics.get('calls_per_minute', 0):.1f}")
        self.query_one("#metric-operations", Static).update(str(metrics.get("total_operations", 0)))
        self.query_one("#metric-guardrails", Static).update(str(metrics.get("total_guardrails", 0)))
        self.query_one("#metric-batches", Static).update(str(metrics.get("batches_completed", 0)))
        self.query_one("#metric-runtime", Static).update(metrics.get("runtime", "0s"))
        self.query_one("#metric-load-profile", Static).update(metrics.get("current_load_profile", "normal"))
