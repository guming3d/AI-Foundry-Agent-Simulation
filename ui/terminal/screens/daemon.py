"""
Daemon simulation screen for the Textual TUI application.

Allows users to run continuous background simulations that mimic
production traffic patterns to AI agents.
"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Button, Input, Log, Select, DataTable
from textual.containers import Vertical, Horizontal
from textual import work
from textual.timer import Timer

from ui.shared.state_manager import get_state_manager, get_state
from src.core.daemon_runner import DaemonRunner, DaemonConfig
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

    #daemon-setup {
        height: auto;
        padding: 0 1;
        margin: 1 0;
        border: solid $secondary;
        background: $panel;
    }

    #daemon-profile {
        width: 1fr;
    }

    #daemon-agents-table {
        height: 8;
        min-height: 6;
        border: solid $secondary;
        background: $surface;
        margin-bottom: 1;
    }

    #config-row {
        height: auto;
        max-height: 8;
        padding: 0 1;
    }

    #config-panel {
        width: 1fr;
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
        width: 14;
        padding-right: 1;
    }

    #metrics-panel {
        height: auto;
        max-height: 12;
        padding: 0 1;
        margin: 1 0;
        border: solid $primary;
        background: $panel;
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

    #daemon-log {
        height: 1fr;
        border: solid $secondary;
        background: $panel;
    }
    """

    def __init__(self):
        super().__init__()
        self.daemon: DaemonRunner = None
        self.metrics_timer: Timer = None
        self.template_loader = TemplateLoader()
        self.profiles = []
        self.selected_profile_id = None
        self.selected_profile = None
        self.agents = []
        self.selected_agent_names = set()
        self.agent_row_keys = {}
        self.is_loading_agents = False

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
            Static("Simulation Setup", classes="section-title"),
            Horizontal(
                Static("Profile:", classes="input-label"),
                Select([], id="daemon-profile", allow_blank=True),
                Button("Refresh Profiles", id="btn-refresh-profiles", variant="default"),
            ),
            Static("Agents", classes="section-title"),
            DataTable(id="daemon-agents-table"),
            Horizontal(
                Button("Refresh Agents", id="btn-refresh-agents", variant="primary"),
                Button("Select All", id="btn-select-all-agents", variant="default"),
                Button("Clear", id="btn-clear-agents", variant="default"),
            ),
            id="daemon-setup",
        )

        yield Horizontal(
            Vertical(
                Horizontal(
                    Static("Interval (s):", classes="input-label"),
                    Input(value="60", id="interval", type="integer"),
                ),
                Horizontal(
                    Static("Min Calls:", classes="input-label"),
                    Input(value="5", id="calls-min", type="integer"),
                ),
                Horizontal(
                    Static("Max Calls:", classes="input-label"),
                    Input(value="15", id="calls-max", type="integer"),
                ),
                id="config-panel",
            ),
            Vertical(
                Horizontal(
                    Static("Threads:", classes="input-label"),
                    Input(value="3", id="threads", type="integer"),
                ),
                Horizontal(
                    Static("Delay (s):", classes="input-label"),
                    Input(value="0.5", id="delay"),
                ),
                Horizontal(
                    Static("Ops Weight %:", classes="input-label"),
                    Input(value="80", id="ops-weight", type="integer"),
                ),
                id="config-panel-2",
            ),
            id="config-row",
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
            id="metrics-panel",
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

        # Start metrics refresh timer
        self.metrics_timer = self.set_interval(1.0, self._refresh_metrics)

    def on_unmount(self) -> None:
        """Cleanup when screen is unmounted."""
        if self.metrics_timer:
            self.metrics_timer.stop()

    def _check_prerequisites(self) -> None:
        """Check if prerequisites are met."""
        log = self.query_one("#daemon-log", Log)

        log.write_line("[*] Daemon Simulation Ready")
        log.write_line("-" * 40)

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
        if self.daemon and self.daemon.is_running:
            metrics = self.daemon.get_metrics()
            self._update_metrics_display(metrics)
            get_state_manager().update_daemon_metrics(metrics)

    def _update_metrics_display(self, metrics: dict) -> None:
        """Update the metrics display widgets."""
        self.query_one("#metric-total-calls", Static).update(str(metrics.get("total_calls", 0)))
        self.query_one("#metric-success-rate", Static).update(f"{metrics.get('success_rate', 0):.1f}%")
        self.query_one("#metric-latency", Static).update(f"{metrics.get('avg_latency_ms', 0):.0f}ms")
        self.query_one("#metric-calls-per-min", Static).update(f"{metrics.get('calls_per_minute', 0):.1f}")
        self.query_one("#metric-operations", Static).update(str(metrics.get("total_operations", 0)))
        self.query_one("#metric-guardrails", Static).update(str(metrics.get("total_guardrails", 0)))
        self.query_one("#metric-batches", Static).update(str(metrics.get("batches_completed", 0)))
        self.query_one("#metric-runtime", Static).update(metrics.get("runtime", "0s"))
        self.query_one("#metric-load-profile", Static).update(metrics.get("current_load_profile", "normal"))

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
        else:
            select.value = None

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

    def action_start_daemon(self) -> None:
        """Start the daemon simulation."""
        if self.daemon and self.daemon.is_running:
            self.notify("Daemon is already running", severity="warning")
            return

        log = self.query_one("#daemon-log", Log)

        # Validate configuration
        try:
            interval = int(self.query_one("#interval", Input).value or "60")
            calls_min = int(self.query_one("#calls-min", Input).value or "5")
            calls_max = int(self.query_one("#calls-max", Input).value or "15")
            threads = int(self.query_one("#threads", Input).value or "3")
            delay = float(self.query_one("#delay", Input).value or "0.5")
            ops_weight = int(self.query_one("#ops-weight", Input).value or "80")
        except ValueError:
            self.notify("Invalid configuration values", severity="error")
            log.write_line("[X] Invalid configuration values")
            return

        profile = self._require_profile(log)
        if not profile:
            return

        selected_agents = self._get_selected_agents()
        if not selected_agents:
            self.notify("Select at least one agent to start the daemon", severity="error")
            log.write_line("[X] No agents selected. Choose agents in Simulation Setup.")
            return

        log.write_line("")
        log.write_line("=" * 50)
        log.write_line("[>] Starting daemon simulation...")
        log.write_line(f"    Interval: {interval}s")
        log.write_line(f"    Calls per batch: {calls_min}-{calls_max}")
        log.write_line(f"    Threads: {threads}, Delay: {delay}s")
        log.write_line(f"    Operations weight: {ops_weight}%")
        log.write_line(f"    Profile: {profile.metadata.name}")
        log.write_line(f"    Agents: {len(selected_agents)} selected")
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
            agents=selected_agents,
            profile=profile,
        )

        if self.daemon.get_agent_count() == 0:
            self.notify("No agents available to run", severity="error")
            log.write_line("[X] No agents available to run")
            return

        log.write_line(f"[+] Loaded {self.daemon.get_agent_count()} agents")

        # Define callbacks
        def log_callback(message: str):
            self.app.call_from_thread(self._log_message, message)

        def metrics_callback(metrics: dict):
            self.app.call_from_thread(self._update_metrics_display, metrics)

        # Start daemon
        if self.daemon.start(config, log_callback=log_callback, metrics_callback=metrics_callback):
            self._update_status_indicator(True)
            get_state_manager().start_daemon()
            self.notify("Daemon started")
            log.write_line("[+] Daemon started successfully")
        else:
            self.notify("Failed to start daemon", severity="error")
            log.write_line("[X] Failed to start daemon")

    def _log_message(self, message: str) -> None:
        """Write a message to the log widget."""
        log = self.query_one("#daemon-log", Log)
        log.write_line(message)

    def action_stop_daemon(self) -> None:
        """Stop the daemon simulation."""
        if not self.daemon or not self.daemon.is_running:
            self.notify("Daemon is not running", severity="warning")
            return

        log = self.query_one("#daemon-log", Log)
        log.write_line("")
        log.write_line("[>] Stopping daemon...")

        self.daemon.stop()
        self._update_status_indicator(False)
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
