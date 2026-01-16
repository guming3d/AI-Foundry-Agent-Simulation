"""
Evaluation tab for the Gradio Web UI.

Allows users to run sample evaluations against selected agents.
"""

import gradio as gr

from src.core.agent_manager import AgentManager
from src.core.evaluation_engine import EvaluationEngine
from src.core.evaluation_templates import EvaluationTemplateLoader
from ui.shared.state_manager import get_state_manager


def create_evaluation_tab():
    """Create the evaluation tab components."""
    loader = EvaluationTemplateLoader()
    templates = loader.list_templates()
    template_labels = [f"{template.display_name} ({template.id})" for template in templates]
    template_lookup = {f"{template.display_name} ({template.id})": template.id for template in templates}

    def refresh_agents():
        """Refresh available agents."""
        manager = AgentManager()
        agents = manager.list_agents()
        choices = [agent.get("name", "") for agent in agents if agent.get("name")]
        status = f"Loaded {len(choices)} agent(s)"
        return gr.Dropdown.update(choices=choices, value=[]), status

    def run_evaluations(selected_templates, selected_agents, progress=gr.Progress()):
        """Run evaluations for the selected agents."""
        if not selected_templates:
            return "Select at least one evaluation template.", [], ""
        if not selected_agents:
            return "Select at least one agent.", [], ""

        template_ids = [template_lookup[label] for label in selected_templates if label in template_lookup]
        logs = []

        def progress_callback(current, total, message):
            if total > 0:
                progress(current / total, desc=message)

        def log_callback(message: str):
            logs.append(message)

        engine = EvaluationEngine()
        try:
            results = engine.run(
                template_ids=template_ids,
                agent_names=selected_agents,
                progress_callback=progress_callback,
                log_callback=log_callback,
            )
        except Exception as exc:
            logs.append(f"[!] Error: {exc}")
            return f"Error: {exc}", [], "\n".join(logs)

        for run_summary in results:
            get_state_manager().add_evaluation_run(run_summary)

        status = f"Completed {len(results)} evaluation(s)."
        return status, results, "\n".join(logs)

    gr.Markdown("## Sample Evaluations")
    gr.Markdown("Pick one or more evaluation templates and apply them to selected agents.")

    template_picker = gr.CheckboxGroup(
        choices=template_labels,
        label="Evaluation Templates",
    )

    with gr.Row():
        agent_picker = gr.Dropdown(
            choices=[],
            multiselect=True,
            label="Agents",
        )
        refresh_btn = gr.Button("Refresh Agents", size="sm")

    status_output = gr.Textbox(label="Status", interactive=False)
    log_output = gr.Textbox(label="Log", lines=8, interactive=False)
    results_output = gr.JSON(label="Evaluation Results")

    run_btn = gr.Button("Run Evaluations", variant="primary")

    refresh_btn.click(
        fn=refresh_agents,
        outputs=[agent_picker, status_output],
    )

    run_btn.click(
        fn=run_evaluations,
        inputs=[template_picker, agent_picker],
        outputs=[status_output, results_output, log_output],
    )
