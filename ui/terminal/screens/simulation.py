"""
Simulation screen for the Textual TUI application.

Allows users to run simulations and monitor progress.
"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Button, Input, ProgressBar, Log, Select
from textual.containers import Vertical, Horizontal
from textual import work

from ui.shared.state_manager import get_state_manager, get_state
from src.core.simulation_engine import SimulationEngine, SimulationConfig


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
    }

    #sim-header {
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
        max-height: 8;
        padding: 0 1;
    }

    #type-panel {
        width: 1fr;
        height: auto;
        padding: 0 1;
    }

    #config-panel {
        width: 2fr;
        height: auto;
        padding: 0 1;
    }

    #config-panel Horizontal {
        height: auto;
    }

    #config-panel Input {
        width: 10;
    }

    .input-label {
        width: 8;
        padding-right: 1;
    }

    #progress-panel {
        height: auto;
        max-height: 4;
        padding: 0 1;
    }

    #log-panel {
        height: 1fr;
        min-height: 10;
        padding: 0 1;
    }

    #sim-log {
        height: 1fr;
        border: solid $primary;
    }

    #sim-type {
        width: 100%;
    }
    """

    def __init__(self):
        super().__init__()
        self.engine = None
        self.simulation_active = False

    def action_go_back(self) -> None:
        """Go back to previous screen."""
        self.app.pop_screen()

    def compose(self) -> ComposeResult:
        # Header with title
        yield Static("Simulation Dashboard", id="title", classes="screen-title")

        # Button bar at top for easy access
        yield Horizontal(
            Button("Run [R]", id="btn-run", variant="primary"),
            Button("Stop [X]", id="btn-stop", variant="error"),
            Button("Back [Esc]", id="btn-back"),
            id="button-bar",
        )

        # Compact config row
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
                id="config-panel",
            ),
            id="config-row",
        )

        # Progress section
        yield Vertical(
            ProgressBar(id="progress-bar", total=100, show_eta=True),
            Static("Ready", id="progress-status"),
            id="progress-panel",
        )

        # Log section (takes remaining space)
        yield Vertical(
            Static("Log:", classes="section-title"),
            Log(id="sim-log", auto_scroll=True),
            id="log-panel",
        )

    def on_mount(self) -> None:
        """Initialize the screen."""
        self._check_prerequisites()

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
            self.action_run_simulation()
        elif button_id == "btn-stop":
            self.action_stop_simulation()
        elif button_id == "btn-back":
            self.app.pop_screen()

    def action_run_simulation(self) -> None:
        """Run the simulation."""
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
            return

        # Get simulation type from Select widget
        select = self.query_one("#sim-type", Select)
        sim_type = str(select.value) if select.value else "operations"

        log.write_line(f"\n[>] Starting {sim_type} simulation...")
        log.write_line(f"    Calls: {num_calls}, Threads: {threads}, Delay: {delay}s")

        # Initialize engine
        try:
            if state.current_profile:
                self.engine = SimulationEngine.from_profile(
                    profile=state.current_profile,
                    agents_csv=state.agents_csv_path,
                )
            else:
                self.engine = SimulationEngine(
                    agents_csv=state.agents_csv_path,
                )
        except Exception as e:
            log.write_line(f"[X] Error initializing engine: {e}")
            self.notify(f"Error: {e}", severity="error")
            return

        config = SimulationConfig(
            num_calls=num_calls,
            threads=threads,
            delay=delay,
        )

        # Run in background thread
        self.run_simulation_in_thread(sim_type, config)

    @work(thread=True, exclusive=True)
    def run_simulation_in_thread(self, sim_type: str, config: SimulationConfig) -> None:
        """Run simulation in a background thread (non-blocking)."""
        self.simulation_active = True

        def progress_callback(current, total, message):
            self.app.call_from_thread(self._update_progress, current, total, message)

        def log_message(msg):
            self.app.call_from_thread(self._log_message, msg)

        try:
            if sim_type == "operations":
                log_message("[>] Running operations simulation...")
                summary = self.engine.run_operations(config, progress_callback)
                self.engine.save_results()
                get_state_manager().set_operation_summary(summary)
                log_message(f"[+] Operations complete: {summary.get('success_rate', 0):.1f}% success rate")

            elif sim_type == "guardrails":
                log_message("[>] Running guardrails simulation...")
                summary = self.engine.run_guardrails(config, progress_callback=progress_callback)
                self.engine.save_results()
                get_state_manager().set_guardrail_summary(summary)
                log_message(f"[+] Guardrails complete: {summary.get('overall_block_rate', 0):.1f}% block rate")

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

                self.engine.save_results()

            log_message("[*] Simulation completed. View results in Results screen.")
            self.app.call_from_thread(self.notify, "Simulation completed!")

        except Exception as e:
            log_message(f"[X] Error: {e}")
            self.app.call_from_thread(self.notify, f"Error: {e}", severity="error")

        finally:
            self.simulation_active = False
            self.app.call_from_thread(self._update_progress, 0, 100, "Ready")

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
            log = self.query_one("#sim-log", Log)
            log.write_line("[!] Simulation stopped by user")
            self.notify("Simulation stopped")
        else:
            self.notify("No simulation running", severity="warning")
