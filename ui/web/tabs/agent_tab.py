"""
Agent creation tab for the Gradio Web UI.

Allows users to create agents and generate code.
"""

import gradio as gr

from ui.shared.state_manager import get_state_manager, get_state
from src.core.agent_manager import AgentManager
from src.codegen.generator import generate_code_for_profile


def create_agent_tab():
    """Create the agent creation tab components."""

    def get_current_config():
        """Get current configuration summary."""
        state = get_state()

        models = ", ".join(state.selected_models) if state.selected_models else "None selected"
        profile = state.current_profile.metadata.name if state.current_profile else "None selected"
        agent_types = len(state.current_profile.agent_types) if state.current_profile else 0

        return f"""**Profile:** {profile}
**Agent Types:** {agent_types}
**Models:** {models}"""

    def calculate_total_agents(org_count, agent_count):
        """Calculate total agents to be created."""
        state = get_state()
        agent_types = len(state.current_profile.agent_types) if state.current_profile else 0
        total = org_count * agent_count * agent_types
        return f"Total agents to create: {total}"

    def get_agents_table():
        """Get created agents as table data."""
        state = get_state()
        data = []
        for agent in state.created_agents:
            data.append([
                agent.name,
                agent.model,
                agent.agent_type or "Unknown",
                "Created",
            ])
        return data

    def create_agents(org_count, agent_count, progress=gr.Progress()):
        """Create agents based on configuration."""
        state = get_state()

        if not state.current_profile:
            return "Error: Please select an industry profile first", get_agents_table()

        if not state.selected_models:
            return "Error: Please select at least one model first", get_agents_table()

        total = org_count * agent_count * len(state.current_profile.agent_types)

        def progress_callback(current, total_count, message):
            progress(current / total_count, desc=message)

        try:
            manager = AgentManager(models=state.selected_models)
            result = manager.create_agents_from_profile(
                profile=state.current_profile,
                agent_count=int(agent_count),
                org_count=int(org_count),
                models=state.selected_models,
                progress_callback=progress_callback,
            )

            # Save to CSV
            csv_path = "created_agents_results.csv"
            manager.save_agents_to_csv(result.created, csv_path)

            # Update state
            get_state_manager().set_created_agents(result.created, csv_path)

            status = f"Created {len(result.created)} agents successfully"
            if result.failed:
                status += f", {len(result.failed)} failed"

            return status, get_agents_table()

        except Exception as e:
            return f"Error: {e}", get_agents_table()

    def generate_code():
        """Generate simulation code."""
        state = get_state()

        if not state.current_profile:
            return "Error: Please select an industry profile first", ""

        try:
            output_dir = "output/generated_code"
            result = generate_code_for_profile(
                profile=state.current_profile,
                output_dir=output_dir,
                agents_csv=state.agents_csv_path,
            )

            get_state_manager().set_generated_code_dir(output_dir)

            files_list = "\n".join(f"- {name}" for name in result.keys())
            return f"Generated files to {output_dir}:\n{files_list}", output_dir

        except Exception as e:
            return f"Error: {e}", ""

    gr.Markdown("## Agent Creation Wizard")

    with gr.Row():
        config_display = gr.Markdown(
            value=get_current_config(),
            label="Current Configuration",
        )
        refresh_config_btn = gr.Button("Refresh Config", size="sm")

    with gr.Row():
        with gr.Column():
            org_count = gr.Number(
                value=1,
                label="Number of Organizations",
                minimum=1,
                maximum=20,
                step=1,
            )

        with gr.Column():
            agent_count = gr.Number(
                value=1,
                label="Agents per Type",
                minimum=1,
                maximum=10,
                step=1,
            )

    total_display = gr.Textbox(
        label="Total Agents",
        value="Total agents to create: 0",
        interactive=False,
    )

    with gr.Row():
        create_btn = gr.Button("Create Agents", variant="primary")
        generate_btn = gr.Button("Generate Code", variant="secondary")

    status_output = gr.Textbox(
        label="Status",
        interactive=False,
    )

    generated_path = gr.Textbox(
        label="Generated Code Path",
        interactive=False,
        visible=False,
    )

    agents_table = gr.Dataframe(
        headers=["Name", "Model", "Type", "Status"],
        value=get_agents_table(),
        label="Created Agents",
    )

    # Event handlers
    refresh_config_btn.click(
        fn=get_current_config,
        outputs=[config_display],
    )

    org_count.change(
        fn=calculate_total_agents,
        inputs=[org_count, agent_count],
        outputs=[total_display],
    )

    agent_count.change(
        fn=calculate_total_agents,
        inputs=[org_count, agent_count],
        outputs=[total_display],
    )

    create_btn.click(
        fn=create_agents,
        inputs=[org_count, agent_count],
        outputs=[status_output, agents_table],
    )

    generate_btn.click(
        fn=generate_code,
        outputs=[status_output, generated_path],
    )
