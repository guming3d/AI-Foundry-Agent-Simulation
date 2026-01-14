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
from .tabs.setup_tab import create_setup_tab

from src.core.env_validator import EnvValidator


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
            1. **Setup** - Configure your environment (if needed)
            2. **Models** - Select models for your agents
            3. **Profiles** - Choose an industry profile
            4. **Agents** - Create agents and generate code
            5. **Simulate** - Run operations and guardrail tests
            6. **Results** - View metrics and analysis
            """
        )

        # Show configuration warning if not configured
        validation = EnvValidator.validate()
        if not validation.is_valid:
            gr.Markdown(
                f"""
                <div style="background-color: #fff3cd; border: 2px solid #ffc107; border-radius: 5px; padding: 15px; margin: 10px 0;">
                    <h3 style="color: #856404; margin-top: 0;">⚠️ Configuration Required</h3>
                    <p style="color: #856404; margin-bottom: 0;">
                        <strong>{validation.error_message}</strong><br>
                        Please go to the <strong>Setup</strong> tab to configure your environment before using other features.
                    </p>
                </div>
                """
            )

        with gr.Tabs() as tabs:
            with gr.TabItem("🔧 Setup", id="setup"):
                create_setup_tab()

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
