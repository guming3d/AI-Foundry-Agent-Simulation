"""
Simulation screen for the Textual TUI application.

Allows users to run simulations and monitor progress.
"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Button, Input, ProgressBar, RichLog, RadioSet, RadioButton
from textual.containers import Container, Vertical, Horizontal
from textual.worker import Worker, WorkerState

from ui.shared.state_manager import get_state_manager, get_state
from src.core.simulation_engine import SimulationEngine, SimulationConfig


class SimulationScreen(Screen):
    """Screen for running simulations."""

    BINDINGS = [
        ("escape", "app.pop_screen()", "Back"),
        ("r", "run_simulation", "Run"),
        ("x", "stop_simulation", "Stop"),
    ]

    def __init__(self):
        super().__init__()
        self.engine = None
        self.current_worker = None

    def compose(self) -> ComposeResult:
        yield Container(
            Static("Simulation Dashboard", id="title", classes="screen-title"),
            Horizontal(
                Vertical(
                    Static("Simulation Type:", classes="label"),
                    RadioSet(
                        RadioButton("Operations", id="radio-ops", value=True),
                        RadioButton("Guardrails", id="radio-guard"),
                        RadioButton("Both", id="radio-both"),
                        id="sim-type",
                    ),
                    id="type-panel",
                ),
                Vertical(
                    Static("Configuration:", classes="label"),
                    Horizontal(
                        Static("Calls:", classes="input-label"),
                        Input(value="50", id="num-calls", type="integer"),
                    ),
                    Horizontal(
                        Static("Threads:", classes="input-label"),
                        Input(value="3", id="threads", type="integer"),
                    ),
                    Horizontal(
                        Static("Delay (s):", classes="input-label"),
                        Input(value="0.5", id="delay"),
                    ),
                    id="config-panel",
                ),
                id="settings-row",
            ),
            Horizontal(
                Button("Run Simulation [R]", id="btn-run", variant="primary"),
                Button("Stop [X]", id="btn-stop", variant="error"),
                Button("Back", id="btn-back"),
                id="button-bar",
            ),
            Vertical(
                Static("Progress:", classes="section-title"),
                ProgressBar(id="progress-bar", total=100, show_eta=True),
                Static(id="progress-status"),
                id="progress-panel",
            ),
            Vertical(
                Static("Log:", classes="section-title"),
                RichLog(id="sim-log", highlight=True, markup=True),
                id="log-panel",
            ),
            id="simulation-container",
        )

    def on_mount(self) -> None:
        """Initialize the screen."""
        self._check_prerequisites()

    def _check_prerequisites(self) -> None:
        """Check if prerequisites are met for simulation."""
        state = get_state()
        log = self.query_one("#sim-log", RichLog)

        if not state.current_profile:
            log.write("[yellow]Warning: No industry profile selected[/yellow]")
        else:
            log.write(f"[green]Profile: {state.current_profile.metadata.name}[/green]")

        if not state.created_agents:
            log.write("[yellow]Warning: No agents created. Using existing CSV if available.[/yellow]")
        else:
            log.write(f"[green]Agents: {len(state.created_agents)} available[/green]")

        log.write("[blue]Ready to run simulation[/blue]")

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
        state = get_state()
        log = self.query_one("#sim-log", RichLog)

        # Get configuration
        try:
            num_calls = int(self.query_one("#num-calls", Input).value or "50")
            threads = int(self.query_one("#threads", Input).value or "3")
            delay = float(self.query_one("#delay", Input).value or "0.5")
        except ValueError:
            self.notify("Invalid configuration values", severity="error")
            return

        # Get simulation type
        radio_set = self.query_one("#sim-type", RadioSet)
        sim_type = "operations"  # default
        for radio in radio_set.query(RadioButton):
            if radio.value:
                if radio.id == "radio-guard":
                    sim_type = "guardrails"
                elif radio.id == "radio-both":
                    sim_type = "both"
                break

        log.write(f"[blue]Starting {sim_type} simulation...[/blue]")
        log.write(f"  Calls: {num_calls}, Threads: {threads}, Delay: {delay}s")

        # Initialize engine
        if state.current_profile:
            self.engine = SimulationEngine.from_profile(
                profile=state.current_profile,
                agents_csv=state.agents_csv_path,
            )
        else:
            self.engine = SimulationEngine(
                agents_csv=state.agents_csv_path,
            )

        config = SimulationConfig(
            num_calls=num_calls,
            threads=threads,
            delay=delay,
        )

        # Run in background
        self.current_worker = self.run_simulation_worker(sim_type, config)

    @property
    def is_running(self) -> bool:
        """Check if a simulation is running."""
        return self.current_worker is not None and self.current_worker.state == WorkerState.RUNNING

    def run_simulation_worker(self, sim_type: str, config: SimulationConfig) -> Worker:
        """Run simulation in a worker thread."""

        def progress_callback(current, total, message):
            self.call_from_thread(self._update_progress, current, total, message)

        async def do_work():
            log = self.query_one("#sim-log", RichLog)

            try:
                if sim_type == "operations":
                    summary = self.engine.run_operations(config, progress_callback)
                    self.engine.save_results()
                    get_state_manager().set_operation_summary(summary)
                    self.call_from_thread(log.write, f"[green]Operations complete: {summary.get('success_rate', 0):.1f}% success rate[/green]")

                elif sim_type == "guardrails":
                    summary = self.engine.run_guardrails(config, progress_callback=progress_callback)
                    self.engine.save_results()
                    get_state_manager().set_guardrail_summary(summary)
                    self.call_from_thread(log.write, f"[green]Guardrails complete: {summary.get('overall_block_rate', 0):.1f}% block rate[/green]")

                else:  # both
                    ops_summary = self.engine.run_operations(config, progress_callback)
                    get_state_manager().set_operation_summary(ops_summary)
                    self.call_from_thread(log.write, f"[green]Operations: {ops_summary.get('success_rate', 0):.1f}% success[/green]")

                    self.engine.clear_metrics()

                    guard_summary = self.engine.run_guardrails(config, progress_callback=progress_callback)
                    get_state_manager().set_guardrail_summary(guard_summary)
                    self.call_from_thread(log.write, f"[green]Guardrails: {guard_summary.get('overall_block_rate', 0):.1f}% blocked[/green]")

                    self.engine.save_results()

            except Exception as e:
                self.call_from_thread(log.write, f"[red]Error: {e}[/red]")

        return self.run_worker(do_work, exclusive=True)

    def _update_progress(self, current: int, total: int, message: str) -> None:
        """Update progress display."""
        progress = self.query_one("#progress-bar", ProgressBar)
        status = self.query_one("#progress-status", Static)

        progress.update(total=total, progress=current)
        status.update(message)

    def action_stop_simulation(self) -> None:
        """Stop the current simulation."""
        if self.engine:
            self.engine.stop()
            log = self.query_one("#sim-log", RichLog)
            log.write("[yellow]Simulation stopped by user[/yellow]")
        if self.current_worker:
            self.current_worker.cancel()
