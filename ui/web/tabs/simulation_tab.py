"""
Simulation tab for the Gradio Web UI.

Allows users to run simulations and monitor progress.
"""

import gradio as gr
import time

from ui.shared.state_manager import get_state_manager, get_state
from src.core.simulation_engine import SimulationEngine, SimulationConfig


def create_simulation_tab():
    """Create the simulation tab components."""

    engine = None

    def get_status():
        """Get current simulation status."""
        state = get_state()
        profile = state.current_profile.metadata.name if state.current_profile else "None"
        agents = len(state.created_agents)
        return f"Profile: {profile} | Agents: {agents}"

    def run_simulation(sim_type, num_calls, threads, delay, progress=gr.Progress()):
        """Run the simulation."""
        state = get_state()

        if not state.current_profile and not state.created_agents:
            yield "Error: No profile or agents configured", []
            return

        # Initialize engine
        if state.current_profile:
            sim_engine = SimulationEngine.from_profile(
                profile=state.current_profile,
                agents_csv=state.agents_csv_path,
            )
        else:
            sim_engine = SimulationEngine(
                agents_csv=state.agents_csv_path,
            )

        config = SimulationConfig(
            num_calls=int(num_calls),
            threads=int(threads),
            delay=float(delay),
        )

        log_entries = []

        def progress_callback(current, total, message):
            progress(current / total, desc=message)
            log_entries.append(f"[{current}/{total}] {message}")

        log_entries.append(f"Starting {sim_type} simulation...")
        log_entries.append(f"Config: {num_calls} calls, {threads} threads, {delay}s delay")
        yield "\n".join(log_entries), log_entries[-5:]

        try:
            if sim_type == "Operations":
                summary = sim_engine.run_operations(config, progress_callback)
                sim_engine.save_results()
                get_state_manager().set_operation_summary(summary)
                log_entries.append(f"Operations complete: {summary.get('success_rate', 0):.1f}% success rate")

            elif sim_type == "Guardrails":
                summary = sim_engine.run_guardrails(config, progress_callback=progress_callback)
                sim_engine.save_results()
                get_state_manager().set_guardrail_summary(summary)
                log_entries.append(f"Guardrails complete: {summary.get('overall_block_rate', 0):.1f}% block rate")

            else:  # Both
                ops_summary = sim_engine.run_operations(config, progress_callback)
                get_state_manager().set_operation_summary(ops_summary)
                log_entries.append(f"Operations: {ops_summary.get('success_rate', 0):.1f}% success")

                sim_engine.clear_metrics()

                guard_summary = sim_engine.run_guardrails(config, progress_callback=progress_callback)
                get_state_manager().set_guardrail_summary(guard_summary)
                log_entries.append(f"Guardrails: {guard_summary.get('overall_block_rate', 0):.1f}% blocked")

                sim_engine.save_results()

            log_entries.append("Simulation completed successfully!")

        except Exception as e:
            log_entries.append(f"Error: {e}")

        yield "\n".join(log_entries), log_entries[-10:]

    gr.Markdown("## Simulation Dashboard")

    status_display = gr.Textbox(
        label="Status",
        value=get_status(),
        interactive=False,
    )

    with gr.Row():
        with gr.Column():
            sim_type = gr.Radio(
                choices=["Operations", "Guardrails", "Both"],
                value="Operations",
                label="Simulation Type",
            )

        with gr.Column():
            num_calls = gr.Number(
                value=50,
                label="Number of Calls/Tests",
                minimum=1,
                maximum=1000,
            )

            threads = gr.Number(
                value=3,
                label="Parallel Threads",
                minimum=1,
                maximum=20,
            )

            delay = gr.Number(
                value=0.5,
                label="Delay (seconds)",
                minimum=0.1,
                maximum=5.0,
            )

    run_btn = gr.Button("Run Simulation", variant="primary")

    with gr.Row():
        log_output = gr.Textbox(
            label="Simulation Log",
            lines=15,
            interactive=False,
        )

    recent_log = gr.Dataframe(
        headers=["Recent Activity"],
        label="Recent Log Entries",
        visible=False,
    )

    # Event handlers
    run_btn.click(
        fn=run_simulation,
        inputs=[sim_type, num_calls, threads, delay],
        outputs=[log_output, recent_log],
    )
