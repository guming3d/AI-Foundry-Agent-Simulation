"""
Main Gradio Web UI application for Azure AI Foundry Control-Plane Batch Agent Operation.

Provides a web-based interface for:
- Batch agent creation (100+ agents)
- Model selection and deployment
- Industry profile management
- Parallel simulation execution
- Real-time metrics and visualization
"""

import gradio as gr

from .tabs.model_tab import create_model_tab
from .tabs.profile_tab import create_profile_tab
from .tabs.agent_tab import create_agent_tab
from .tabs.simulation_tab import create_simulation_tab
from .tabs.results_tab import create_results_tab


def create_app() -> gr.Blocks:
    """
    Create the Gradio application for batch agent operations.

    Returns:
        gr.Blocks application
    """
    with gr.Blocks(
        title="Azure AI Foundry Control-Plane Batch Agent Operation",
        theme=gr.themes.Soft(
            primary_hue="blue",
            secondary_hue="slate",
        ),
    ) as app:
        gr.Markdown(
            """
            # Azure AI Foundry Control-Plane Batch Agent Operation

            Batch create, test, and monitor AI agents at scale with Azure AI Foundry Control Plane.

            **Quick Start:**
            1. **Models** - Select models for your agents
            2. **Profiles** - Choose an industry profile
            3. **Agents** - Create agents and generate code
            4. **Simulate** - Run operations and guardrail tests
            5. **Results** - View metrics and analysis
            """
        )

        with gr.Tabs() as tabs:
            with gr.TabItem("Models", id="models"):
                create_model_tab()

            with gr.TabItem("Profiles", id="profiles"):
                create_profile_tab()

            with gr.TabItem("Agents", id="agents"):
                create_agent_tab()

            with gr.TabItem("Simulate", id="simulate"):
                create_simulation_tab()

            with gr.TabItem("Results", id="results"):
                create_results_tab()

    return app


def run_web_ui(share: bool = False, server_port: int = 7860):
    """
    Run the Gradio web UI.

    Args:
        share: Whether to create a public share link
        server_port: Port to run the server on
    """
    app = create_app()
    app.launch(share=share, server_port=server_port)


if __name__ == "__main__":
    run_web_ui()
