"""
Workflow creation tab for the Gradio Web UI.

Allows users to batch create workflow agents based on industry profiles.
"""

import gradio as gr

from ui.shared.state_manager import get_state_manager, get_state
from src.core.workflow_manager import WorkflowManager


def create_workflow_tab():
    """Create the workflow tab components."""

    # ===== Manage Existing Workflows Functions =====

    def list_project_workflows():
        """Fetch all workflow agents from Azure project."""
        try:
            manager = WorkflowManager()
            workflows = manager.list_workflows()
            return workflows
        except Exception as e:
            print(f"Error listing workflows: {e}")
            return []

    def get_project_workflows_table():
        """Get project workflows as table data."""
        workflows = list_project_workflows()
        data = []
        for workflow in workflows:
            data.append([
                workflow.get("name", ""),
                workflow.get("id", ""),
                workflow.get("version", "Unknown"),
            ])
        return data

    def get_workflow_count_display():
        """Get the current workflow count display text."""
        workflows = list_project_workflows()
        count = len(workflows)
        if count == 0:
            return "**No workflows found in the project**"
        return f"**Total workflows in project: {count}**"

    def refresh_project_workflows():
        """Refresh the project workflows list."""
        return get_workflow_count_display(), get_project_workflows_table()

    def get_current_config():
        state = get_state()
        models = ", ".join(state.selected_models) if state.selected_models else "None selected"
        profile = state.current_profile.metadata.name if state.current_profile else "None selected"
        return f"""**Profile:** {profile}
**Models:** {models}"""

    def get_templates():
        state = get_state()
        if not state.current_profile:
            return []
        return WorkflowManager.build_templates(state.current_profile)

    def get_template_table():
        templates = get_templates()
        data = []
        for template in templates:
            if template.roles:
                roles = " -> ".join(role.agent_type.name for role in template.roles)
            else:
                roles = "Human input"
            data.append([template.name, roles, template.description, template.id])
        return data

    def refresh_templates(org_count, workflow_count):
        templates = get_templates()
        if not templates:
            return (
                "**Select an industry profile to view workflow templates.**",
                [],
                gr.CheckboxGroup.update(choices=[], value=[]),
                "Total workflows to create: 0",
            )

        choices = [(template.name, template.id) for template in templates]
        default_ids = [template.id for template in templates]
        return (
            f"**Loaded {len(templates)} workflow templates.**",
            get_template_table(),
            gr.CheckboxGroup.update(choices=choices, value=default_ids),
            calculate_total_workflows(org_count, workflow_count, default_ids),
        )

    def select_all_templates(org_count, workflow_count):
        templates = get_templates()
        choices = [(template.name, template.id) for template in templates]
        selected = [template.id for template in templates]
        return (
            gr.CheckboxGroup.update(
                choices=choices,
                value=selected,
            ),
            calculate_total_workflows(org_count, workflow_count, selected),
        )

    def clear_templates(org_count, workflow_count):
        templates = get_templates()
        choices = [(template.name, template.id) for template in templates]
        return (
            gr.CheckboxGroup.update(choices=choices, value=[]),
            calculate_total_workflows(org_count, workflow_count, []),
        )

    def calculate_total_workflows(org_count, workflow_count, selected_templates):
        try:
            org_count = int(org_count)
            workflow_count = int(workflow_count)
        except (TypeError, ValueError):
            org_count = 1
            workflow_count = 1

        template_count = len(selected_templates or [])
        total = org_count * workflow_count * template_count
        return f"Total workflows to create: {total}"

    def get_created_workflows_table():
        state = get_state()
        data = []
        for workflow in state.created_workflows:
            data.append([
                workflow.name,
                workflow.template_name,
                workflow.org_id,
                workflow.version,
            ])
        return data

    def create_workflows(selected_templates, org_count, workflow_count, progress=gr.Progress()):
        state = get_state()
        if not state.current_profile:
            return (
                "Error: Please select an industry profile first",
                get_created_workflows_table(),
                get_workflow_count_display(),
                get_project_workflows_table(),
            )

        if not state.selected_models:
            return (
                "Error: Please select at least one model first",
                get_created_workflows_table(),
                get_workflow_count_display(),
                get_project_workflows_table(),
            )

        if not selected_templates:
            return (
                "Error: Select at least one workflow template",
                get_created_workflows_table(),
                get_workflow_count_display(),
                get_project_workflows_table(),
            )

        try:
            templates = WorkflowManager.build_templates(state.current_profile)
            template_ids = [template.id for template in templates]
            selected_ids = [template_id for template_id in selected_templates if template_id in template_ids]

            def progress_callback(current, total, message):
                if total > 0:
                    progress(current / total, desc=message)

            manager = WorkflowManager(models=state.selected_models)
            result = manager.create_workflows_from_profile(
                profile=state.current_profile,
                template_ids=selected_ids,
                workflows_per_template=int(workflow_count),
                org_count=int(org_count),
                models=state.selected_models,
                progress_callback=progress_callback,
            )

            existing = list(state.created_workflows)
            get_state_manager().set_created_workflows(existing + result.created)

            status = f"Created {len(result.created)} workflow(s)"
            if result.failed:
                status += f", {len(result.failed)} failed"

            return (
                status,
                get_created_workflows_table(),
                get_workflow_count_display(),
                get_project_workflows_table(),
            )

        except Exception as e:
            return (
                f"Error: {e}",
                get_created_workflows_table(),
                get_workflow_count_display(),
                get_project_workflows_table(),
            )

    gr.Markdown("## Manage Existing Workflows")
    gr.Markdown("View workflows currently in your Azure AI Foundry project.")

    with gr.Row():
        workflow_count_display = gr.Markdown(
            value=get_workflow_count_display(),
        )
        refresh_workflows_btn = gr.Button("Refresh", size="sm")

    project_workflows_table = gr.Dataframe(
        headers=["Name", "ID", "Version"],
        value=get_project_workflows_table(),
        label="Project Workflows",
        interactive=False,
        wrap=True,
    )

    gr.Markdown("---")

    gr.Markdown("## Workflow Builder")
    gr.Markdown("Batch create multi-agent workflows based on the selected industry profile.")

    with gr.Row():
        config_display = gr.Markdown(value=get_current_config())
        refresh_config_btn = gr.Button("Refresh Config", size="sm")

    gr.Markdown("### Workflow Templates")
    template_status = gr.Markdown(value="**Select an industry profile to view workflow templates.**")

    template_table = gr.Dataframe(
        headers=["Template", "Roles", "Description", "Id"],
        value=get_template_table(),
        label="Template details",
        interactive=False,
        wrap=True,
    )

    template_selector = gr.CheckboxGroup(
        choices=[],
        label="Select templates to create",
    )

    with gr.Row():
        refresh_templates_btn = gr.Button("Refresh Templates", size="sm")
        select_all_btn = gr.Button("Select All", size="sm")
        clear_btn = gr.Button("Clear Selection", size="sm")

    gr.Markdown("### Workflow Configuration")
    with gr.Row():
        org_count = gr.Number(
            value=1,
            label="Number of Organizations",
            minimum=1,
            maximum=20,
            step=1,
        )
        workflow_count = gr.Number(
            value=1,
            label="Workflows per Template",
            minimum=1,
            maximum=10,
            step=1,
        )

    total_display = gr.Textbox(
        label="Total Workflows",
        value="Total workflows to create: 0",
        interactive=False,
    )

    create_btn = gr.Button("Create Workflows", variant="primary")
    status_output = gr.Textbox(
        label="Status",
        interactive=False,
    )

    workflows_table = gr.Dataframe(
        headers=["Name", "Template", "Org", "Version"],
        value=get_created_workflows_table(),
        label="Created Workflows",
    )

    refresh_workflows_btn.click(
        fn=refresh_project_workflows,
        outputs=[workflow_count_display, project_workflows_table],
    )

    refresh_config_btn.click(
        fn=get_current_config,
        outputs=[config_display],
    )

    refresh_templates_btn.click(
        fn=refresh_templates,
        inputs=[org_count, workflow_count],
        outputs=[template_status, template_table, template_selector, total_display],
    )

    select_all_btn.click(
        fn=select_all_templates,
        inputs=[org_count, workflow_count],
        outputs=[template_selector, total_display],
    )

    clear_btn.click(
        fn=clear_templates,
        inputs=[org_count, workflow_count],
        outputs=[template_selector, total_display],
    )

    template_selector.change(
        fn=calculate_total_workflows,
        inputs=[org_count, workflow_count, template_selector],
        outputs=[total_display],
    )

    org_count.change(
        fn=calculate_total_workflows,
        inputs=[org_count, workflow_count, template_selector],
        outputs=[total_display],
    )

    workflow_count.change(
        fn=calculate_total_workflows,
        inputs=[org_count, workflow_count, template_selector],
        outputs=[total_display],
    )

    create_btn.click(
        fn=create_workflows,
        inputs=[template_selector, org_count, workflow_count],
        outputs=[status_output, workflows_table, workflow_count_display, project_workflows_table],
    )
