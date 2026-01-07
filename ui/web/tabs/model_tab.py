"""
Model selection tab for the Gradio Web UI.

Allows users to select models for agent deployment.
"""

import gradio as gr

from ui.shared.state_manager import get_state_manager, get_state
from src.core.model_manager import ModelManager


def create_model_tab():
    """Create the model selection tab components."""

    model_manager = ModelManager()

    def get_available_models():
        """Get list of available model names."""
        models = model_manager.list_available_models()
        return [m.name for m in models]

    def get_model_info():
        """Get model information as a DataFrame."""
        models = model_manager.list_available_models()
        data = []
        state = get_state()
        selected = set(state.selected_models)

        for model in models:
            is_selected = "Yes" if model.name in selected else "No"
            capabilities = ", ".join(model.capabilities) if model.capabilities else "N/A"
            data.append([model.name, is_selected, capabilities])

        return data

    def update_selection(selected_models):
        """Update the selected models in state."""
        if selected_models:
            get_state_manager().set_selected_models(selected_models)
            return f"Selected {len(selected_models)} model(s): {', '.join(selected_models)}"
        return "No models selected"

    def refresh_models():
        """Refresh the model list."""
        model_manager.refresh_cache()
        return get_model_info(), get_available_models()

    gr.Markdown("## Model Selection")
    gr.Markdown("Select models to use for your agents. These will be randomly assigned during agent creation.")

    with gr.Row():
        with gr.Column(scale=2):
            model_table = gr.Dataframe(
                headers=["Model", "Selected", "Capabilities"],
                value=get_model_info(),
                interactive=False,
                label="Available Models",
            )

        with gr.Column(scale=1):
            model_checkboxes = gr.CheckboxGroup(
                choices=get_available_models(),
                value=get_state().selected_models,
                label="Select Models",
            )

            selection_status = gr.Textbox(
                label="Selection Status",
                value=f"Selected: {len(get_state().selected_models)} model(s)",
                interactive=False,
            )

    with gr.Row():
        refresh_btn = gr.Button("Refresh Models", variant="secondary")
        save_btn = gr.Button("Save Selection", variant="primary")

    # Event handlers
    model_checkboxes.change(
        fn=update_selection,
        inputs=[model_checkboxes],
        outputs=[selection_status],
    )

    refresh_btn.click(
        fn=refresh_models,
        outputs=[model_table, model_checkboxes],
    )

    save_btn.click(
        fn=update_selection,
        inputs=[model_checkboxes],
        outputs=[selection_status],
    )
