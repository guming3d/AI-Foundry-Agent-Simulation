"""
Industry profile tab for the Gradio Web UI.

Allows users to browse and select industry profiles.
"""

import gradio as gr
import yaml

from ui.shared.state_manager import get_state_manager, get_state
from src.templates.template_loader import TemplateLoader


def create_profile_tab():
    """Create the industry profile tab components."""

    loader = TemplateLoader()

    def get_profile_list():
        """Get list of available profiles."""
        return loader.list_templates()

    def get_profile_info():
        """Get profile information as a DataFrame."""
        data = []
        templates = loader.list_templates()

        for template_id in templates:
            try:
                info = loader.get_template_info(template_id)
                data.append([
                    info["id"],
                    info["name"],
                    info["agent_types"],
                    info["departments"],
                ])
            except:
                data.append([template_id, "Error loading", "-", "-"])

        return data

    def load_profile_details(profile_id):
        """Load and display profile details."""
        if not profile_id:
            return "Select a profile to view details", ""

        try:
            profile = loader.load_template(profile_id)

            details = f"""## {profile.metadata.name}

**Version:** {profile.metadata.version}

**Description:** {profile.metadata.description or 'N/A'}

### Organization
- **Prefix:** {profile.organization.prefix}
- **Departments:** {len(profile.organization.departments)}

### Agent Types ({len(profile.agent_types)})
"""
            for at in profile.agent_types:
                details += f"- **{at.name}** ({at.id})\n"

            details += f"""
### Models
- **Preferred:** {', '.join(profile.models.preferred) or 'None'}
- **Allowed:** {', '.join(profile.models.allowed) or 'None'}

### Guardrail Tests
"""
            categories = profile.guardrail_tests.get_non_empty_categories()
            for cat, tests in categories.items():
                details += f"- {cat}: {len(tests)} tests\n"

            # YAML preview
            yaml_content = yaml.dump(
                loader._profile_to_dict(profile),
                default_flow_style=False,
                allow_unicode=True,
            )

            return details, yaml_content

        except Exception as e:
            return f"Error loading profile: {e}", ""

    def select_profile(profile_id):
        """Select a profile and update state."""
        if not profile_id:
            return "Please select a profile first"

        try:
            profile = loader.load_template(profile_id)
            get_state_manager().set_profile(profile, profile_id)
            return f"Selected profile: {profile.metadata.name}"
        except Exception as e:
            return f"Error selecting profile: {e}"

    def get_current_profile_status():
        """Get the current profile selection status."""
        state = get_state()
        if state.current_profile:
            return f"Current: {state.current_profile.metadata.name}"
        return "No profile selected"

    gr.Markdown("## Industry Profiles")
    gr.Markdown("Select an industry profile to configure your agents.")

    with gr.Row():
        profile_status = gr.Textbox(
            label="Current Selection",
            value=get_current_profile_status(),
            interactive=False,
        )

    with gr.Row():
        with gr.Column(scale=1):
            profile_table = gr.Dataframe(
                headers=["ID", "Name", "Agent Types", "Departments"],
                value=get_profile_info(),
                interactive=False,
                label="Available Profiles",
            )

            profile_dropdown = gr.Dropdown(
                choices=get_profile_list(),
                label="Select Profile",
                value=get_state().current_profile_id,
            )

            with gr.Row():
                view_btn = gr.Button("View Details", variant="secondary")
                select_btn = gr.Button("Select Profile", variant="primary")

        with gr.Column(scale=2):
            profile_details = gr.Markdown(
                value="Select a profile to view details",
                label="Profile Details",
            )

            with gr.Accordion("YAML Configuration", open=False):
                yaml_viewer = gr.Code(
                    language="yaml",
                    label="Profile YAML",
                    interactive=False,
                )

    # Event handlers
    view_btn.click(
        fn=load_profile_details,
        inputs=[profile_dropdown],
        outputs=[profile_details, yaml_viewer],
    )

    profile_dropdown.change(
        fn=load_profile_details,
        inputs=[profile_dropdown],
        outputs=[profile_details, yaml_viewer],
    )

    select_btn.click(
        fn=select_profile,
        inputs=[profile_dropdown],
        outputs=[profile_status],
    )
