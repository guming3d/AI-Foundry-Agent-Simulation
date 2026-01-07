from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Optional

from .agent_generation import generate_agents
from .codegen import generate_workspace
from .constants import (
    APP_NAME,
    DEFAULT_TEMPLATES_DIR,
    DEFAULT_WORKSPACES_DIR,
    MAX_SELECTED_MODELS,
    MIN_SELECTED_MODELS,
)
from .errors import FoundryDemoError, MissingDependencyError
from .results import write_created_agents_csv, write_failed_agents_csv
from .templates import list_industry_templates
from .workspace import create_workspace, write_generated_agents, write_selected_models


def _require_gradio():  # pragma: no cover
    try:
        import gradio as gr  # type: ignore
    except Exception as exc:
        raise MissingDependencyError("Missing dependency: gradio. Install with `pip install gradio`.") from exc
    return gr


def build_app():  # pragma: no cover
    gr = _require_gradio()

    templates = list_industry_templates(DEFAULT_TEMPLATES_DIR)
    template_by_id = {t.template_id: t for t in templates}

    def load_deployments(endpoint: str):
        endpoint = (endpoint or "").strip()
        if not endpoint:
            return gr.update(choices=[], value=[]), "Missing PROJECT_ENDPOINT."

        try:
            from .azure_ops import FoundryProject

            project = FoundryProject(endpoint=endpoint)
            deployments = project.list_deployments()
        except MissingDependencyError as exc:
            return gr.update(choices=[], value=[]), str(exc)
        except Exception as exc:  # noqa: BLE001
            return gr.update(choices=[], value=[]), f"Failed to load deployments: {exc}"

        choices = [d.name for d in deployments if d.name]
        details = "\n".join(
            [
                f"- {d.name} ({' / '.join([p for p in [d.model_publisher, d.model_name] if p])})"
                for d in deployments
            ]
        )
        return gr.update(choices=choices, value=[]), f"Loaded {len(choices)} deployments:\n{details}"

    def generate_click(
        endpoint: str,
        selected_models: list[str],
        manual_models: str,
        template_id: str,
        total_agents: float,
        org_id: str,
        seed: float,
        include_daemon: bool,
        create_now: bool,
        workspace_name: str,
    ):
        try:
            endpoint = (endpoint or "").strip()
            if not endpoint:
                raise FoundryDemoError("PROJECT_ENDPOINT is required.")

            template = template_by_id.get(template_id)
            if template is None:
                raise FoundryDemoError("Select an industry template.")

            models = [m.strip() for m in (selected_models or []) if m.strip()]
            if not models:
                models = [m.strip() for m in (manual_models or "").split(",") if m.strip()]

            if not (MIN_SELECTED_MODELS <= len(models) <= MAX_SELECTED_MODELS):
                raise FoundryDemoError(f"Select {MIN_SELECTED_MODELS}-{MAX_SELECTED_MODELS} models (got {len(models)}).")

            try:
                total_agents_int = int(total_agents)
            except Exception as exc:  # noqa: BLE001
                raise FoundryDemoError(f"Invalid total_agents: {total_agents!r}") from exc

            org_id_value: Optional[str] = (org_id or "").strip() or None
            seed_value: Optional[int] = int(seed) if seed is not None and str(seed).strip() != "" else None

            agents = generate_agents(
                template=template,
                total_agents=total_agents_int,
                models=models,
                org_id=org_id_value,
                seed=seed_value,
            )

            ws = create_workspace(DEFAULT_WORKSPACES_DIR, name=(workspace_name or "").strip() or None)
            (ws / ".env").write_text(f"PROJECT_ENDPOINT={endpoint}\n", encoding="utf-8")
            write_selected_models(ws, models)
            write_generated_agents(ws, agents)
            artifacts = generate_workspace(output_dir=ws, template=template, agents=agents, include_daemon=include_daemon)

            if create_now:
                try:
                    from .azure_ops import FoundryProject

                    project = FoundryProject(endpoint=endpoint)
                    created, failed = project.create_agents(agents=agents)
                    write_created_agents_csv(ws / "created_agents_results.csv", created)
                    if failed:
                        write_failed_agents_csv(ws / "failed_agents_results.csv", failed)
                except Exception as exc:  # noqa: BLE001
                    raise FoundryDemoError(f"Agent creation failed: {exc}") from exc

            zip_path = shutil.make_archive(str(ws), "zip", root_dir=str(ws))
            summary = "\n".join(
                [
                    f"Workspace: {ws}",
                    f"Artifacts: {', '.join(sorted(p.name for p in artifacts.values()))}",
                    f"Zip: {zip_path}",
                    "Next: unzip and follow README_GENERATED.md",
                ]
            )
            return summary, zip_path
        except FoundryDemoError as exc:
            return f"Error: {exc}", None

    with gr.Blocks(title=APP_NAME) as demo:
        gr.Markdown(f"# {APP_NAME}\nGenerate agent fleets + simulation code for Azure AI Foundry demos.")

        with gr.Row():
            endpoint = gr.Textbox(
                label="PROJECT_ENDPOINT",
                value=os.environ.get("PROJECT_ENDPOINT", ""),
                placeholder="https://<resource>.services.ai.azure.com/api/projects/<project>",
            )
            load_btn = gr.Button("Load deployed models", variant="primary")

        deployed_models = gr.CheckboxGroup(label=f"Deployed models (select {MIN_SELECTED_MODELS}-{MAX_SELECTED_MODELS})", choices=[])
        manual_models = gr.Textbox(
            label="Manual models (fallback, comma-separated)",
            placeholder="gpt-4.1-mini,gpt-5.2-chat,...",
        )
        deployments_status = gr.Markdown()

        template_id = gr.Dropdown(
            label="Industry template",
            choices=[t.template_id for t in templates],
            value=templates[0].template_id if templates else None,
        )
        total_agents = gr.Number(label="Total agents", value=36, precision=0)
        org_id = gr.Textbox(label="Org ID override (optional)", placeholder="ORG01")
        seed = gr.Number(label="Random seed (optional)", value=None, precision=0)
        include_daemon = gr.Checkbox(label="Include daemon", value=True)
        create_now = gr.Checkbox(label="Create agents in Foundry now (requires auth)", value=False)
        workspace_name = gr.Textbox(label="Workspace name (optional)", placeholder="e.g., contoso-retail-demo")

        gen_btn = gr.Button("Generate workspace", variant="success")
        output = gr.Textbox(label="Status", lines=8)
        zip_file = gr.File(label="Download workspace (.zip)")

        load_btn.click(load_deployments, inputs=[endpoint], outputs=[deployed_models, deployments_status])
        gen_btn.click(
            generate_click,
            inputs=[
                endpoint,
                deployed_models,
                manual_models,
                template_id,
                total_agents,
                org_id,
                seed,
                include_daemon,
                create_now,
                workspace_name,
            ],
            outputs=[output, zip_file],
        )

    return demo


def main() -> None:  # pragma: no cover
    app = build_app()
    app.launch()


if __name__ == "__main__":  # pragma: no cover
    main()

