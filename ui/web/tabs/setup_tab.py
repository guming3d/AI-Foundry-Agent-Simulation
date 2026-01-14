"""
Setup tab for the Gradio Web UI.

Allows users to configure environment variables.
"""

import gradio as gr

from src.core.env_validator import EnvValidator


def create_setup_tab():
    """Create the setup/configuration tab components."""

    def get_current_status():
        """Get current configuration status."""
        validation = EnvValidator.validate()

        if validation.is_valid:
            endpoint = EnvValidator.get_endpoint()
            return f"""✅ **Environment Configured**

**Current Endpoint:** {endpoint}

Your environment is properly configured and ready to use."""
        else:
            return f"""⚠️ **Configuration Required**

**Status:** {validation.error_message}

Please enter your Azure AI Foundry project endpoint below to continue."""

    def get_setup_guide():
        """Get the setup guide text."""
        return EnvValidator._build_setup_guide()

    def save_configuration(endpoint):
        """Save the project endpoint to .env file."""
        if not endpoint or not endpoint.strip():
            return "❌ Please enter a valid project endpoint", get_current_status()

        success, message = EnvValidator.update_env_file(endpoint.strip())

        if success:
            return f"✅ {message}\n\nEnvironment configured successfully! You can now use all features.", get_current_status()
        else:
            return f"❌ {message}", get_current_status()

    def validate_endpoint(endpoint):
        """Validate endpoint format as user types."""
        if not endpoint:
            return ""

        if not endpoint.startswith("https://"):
            return "⚠️ Endpoint should start with https://"

        if "services.ai.azure.com" not in endpoint:
            return "⚠️ Should contain 'services.ai.azure.com'"

        return "✓ Format looks correct"

    gr.Markdown("## Environment Setup")

    # Status display
    status_box = gr.Markdown(
        value=get_current_status(),
        label="Configuration Status"
    )

    gr.Markdown("---")

    # Configuration section
    gr.Markdown("### Configure Project Endpoint")

    with gr.Row():
        with gr.Column(scale=2):
            endpoint_input = gr.Textbox(
                label="Azure AI Foundry Project Endpoint",
                placeholder="https://your-project.services.ai.azure.com/api/projects/your-project",
                value=EnvValidator.get_endpoint() or "",
                lines=1
            )

            validation_msg = gr.Markdown(value="", visible=True)

            endpoint_input.change(
                fn=validate_endpoint,
                inputs=[endpoint_input],
                outputs=[validation_msg]
            )

        with gr.Column(scale=1):
            save_btn = gr.Button("Save Configuration", variant="primary", size="lg")

    result_message = gr.Markdown(value="", visible=True)

    save_btn.click(
        fn=save_configuration,
        inputs=[endpoint_input],
        outputs=[result_message, status_box]
    )

    gr.Markdown("---")

    # Setup guide
    gr.Markdown("### Setup Guide")

    with gr.Accordion("How to find your Project Endpoint", open=False):
        gr.Markdown(get_setup_guide())

    # Quick reference
    with gr.Accordion("Configuration File Details", open=False):
        gr.Markdown("""
### About the .env File

The `.env` file stores your environment configuration. It should be located in the project root directory.

**File Location:** `./env`

**Format:**
```
PROJECT_ENDPOINT=https://your-project.services.ai.azure.com/api/projects/your-project-id
```

**Security:**
- The .env file is excluded from git (in .gitignore)
- Never commit secrets or credentials to version control
- Keep your project endpoint private

**Manual Configuration:**
You can also manually create or edit the .env file:
1. Copy `.env.example` to `.env` (if available)
2. Add your PROJECT_ENDPOINT
3. Save the file
4. Restart the application
        """)

    return status_box
