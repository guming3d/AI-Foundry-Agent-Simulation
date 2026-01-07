from __future__ import annotations

import os
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


def _require_textual():  # pragma: no cover
    try:
        from textual import on
        from textual.app import App, ComposeResult
        from textual.containers import Horizontal, Vertical
        from textual.widgets import (
            Button,
            Checkbox,
            Footer,
            Header,
            Input,
            Label,
            Select,
            SelectionList,
            Static,
            TabbedContent,
            TabPane,
        )
        from textual.widgets.selection_list import Selection
    except Exception as exc:
        raise MissingDependencyError("Missing dependency: textual. Install with `pip install textual`.") from exc

    return {
        "on": on,
        "App": App,
        "ComposeResult": ComposeResult,
        "Horizontal": Horizontal,
        "Vertical": Vertical,
        "Button": Button,
        "Checkbox": Checkbox,
        "Footer": Footer,
        "Header": Header,
        "Input": Input,
        "Label": Label,
        "Select": Select,
        "SelectionList": SelectionList,
        "Selection": Selection,
        "Static": Static,
        "TabbedContent": TabbedContent,
        "TabPane": TabPane,
    }


_t = _require_textual()
on = _t["on"]
App = _t["App"]
ComposeResult = _t["ComposeResult"]
Horizontal = _t["Horizontal"]
Vertical = _t["Vertical"]
Button = _t["Button"]
Checkbox = _t["Checkbox"]
Footer = _t["Footer"]
Header = _t["Header"]
Input = _t["Input"]
Label = _t["Label"]
Select = _t["Select"]
SelectionList = _t["SelectionList"]
Selection = _t["Selection"]
Static = _t["Static"]
TabbedContent = _t["TabbedContent"]
TabPane = _t["TabPane"]


class FoundryDemoTUI(App):  # type: ignore[misc]
    CSS = """
    Screen {
        align: center middle;
    }

    #app {
        width: 120;
        height: 95%;
        border: round $primary;
        padding: 1 2;
    }

    .row {
        height: auto;
        margin: 1 0;
    }

    Input {
        width: 1fr;
    }

    SelectionList {
        height: 14;
        border: round $surface;
    }

    #status {
        height: auto;
        margin-top: 1;
        border: round $surface;
        padding: 1 1;
    }

    #industry_details {
        border: round $surface;
        padding: 1 1;
        height: 12;
    }
    """

    BINDINGS = [("q", "quit", "Quit")]

    def __init__(self) -> None:
        super().__init__()
        self._templates = list_industry_templates(DEFAULT_TEMPLATES_DIR)
        self._template_by_id = {t.template_id: t for t in self._templates}
        self._generated_workspace: Optional[Path] = None

    def compose(self) -> ComposeResult:  # type: ignore[override]
        yield Header(show_clock=True)
        with Vertical(id="app"):
            yield Label(f"{APP_NAME}", id="title")
            with TabbedContent():
                with TabPane("Setup"):
                    yield Label("PROJECT_ENDPOINT (AI Foundry Project endpoint):")
                    yield Input(value=os.environ.get("PROJECT_ENDPOINT", ""), id="endpoint")
                    with Horizontal(classes="row"):
                        yield Button("Load deployed models", id="load_models", variant="primary")
                        yield Button("Clear models", id="clear_models")
                    yield Static("Tip: set PROJECT_ENDPOINT in a local `.env` file for generated workspaces.", classes="row")

                with TabPane("Models"):
                    yield Label(f"Select {MIN_SELECTED_MODELS}-{MAX_SELECTED_MODELS} deployed model deployments:")
                    yield SelectionList(id="models_list")
                    yield Label("Fallback: enter model deployment names (comma-separated):")
                    yield Input(placeholder="gpt-4.1-mini,gpt-5.2-chat,...", id="manual_models")

                with TabPane("Industry"):
                    yield Label("Select an industry template (editable YAML in `industry_templates/`):")
                    yield Select(
                        options=[(t.display_name, t.template_id) for t in self._templates],
                        value=self._templates[0].template_id if self._templates else Select.BLANK,
                        allow_blank=not bool(self._templates),
                        id="industry_select",
                    )
                    yield Static("", id="industry_details")

                with TabPane("Agents"):
                    yield Label("Agent generation settings:")
                    with Vertical(classes="row"):
                        yield Label("Total agents:")
                        yield Input(value="36", id="total_agents")
                        yield Label("Org ID (optional override):")
                        yield Input(placeholder="ORG01", id="org_id")
                        yield Label("Random seed (optional):")
                        yield Input(placeholder="e.g., 42", id="seed")

                with TabPane("Generate"):
                    yield Label("Workspace output:")
                    yield Input(placeholder="Optional workspace name", id="workspace_name")
                    yield Checkbox("Include daemon (24/7 background simulation)", value=True, id="include_daemon")
                    yield Checkbox("Create agents in Foundry now (requires Azure auth)", value=False, id="create_now")
                    yield Button("Generate workspace", id="generate", variant="success")

            yield Static("", id="status")

        yield Footer()

    def on_mount(self) -> None:  # type: ignore[override]
        self._update_industry_details()
        self._set_status("Ready.")

    @on(Button.Pressed, "#load_models")
    def load_models(self) -> None:
        endpoint = self.query_one("#endpoint", Input).value.strip()
        if not endpoint:
            self._set_status("Missing PROJECT_ENDPOINT.")
            return

        try:
            from .azure_ops import FoundryProject

            project = FoundryProject(endpoint=endpoint)
            deployments = project.list_deployments()
        except MissingDependencyError as exc:
            self._set_status(str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            self._set_status(f"Failed to load deployments: {exc}")
            return

        models_list = self.query_one("#models_list", SelectionList)
        models_list.clear_options()

        selections = []
        for d in deployments:
            label = d.name
            details = " / ".join([p for p in [d.model_publisher, d.model_name] if p])
            if details:
                label = f"{label} ({details})"
            selections.append(Selection(label, d.name, initial_state=False))

        models_list.add_options(selections)
        self._set_status(f"Loaded {len(selections)} deployments. Select {MIN_SELECTED_MODELS}-{MAX_SELECTED_MODELS}.")

    @on(Button.Pressed, "#clear_models")
    def clear_models(self) -> None:
        models_list = self.query_one("#models_list", SelectionList)
        models_list.clear_options()
        self.query_one("#manual_models", Input).value = ""
        self._set_status("Cleared models selection.")

    @on(Select.Changed, "#industry_select")
    def industry_changed(self) -> None:
        self._update_industry_details()

    @on(Button.Pressed, "#generate")
    def generate_clicked(self) -> None:
        try:
            self._generate()
        except FoundryDemoError as exc:
            self._set_status(f"Error: {exc}")
        except Exception as exc:  # noqa: BLE001
            self._set_status(f"Unexpected error: {exc}")

    def _generate(self) -> None:
        endpoint = self.query_one("#endpoint", Input).value.strip()
        if not endpoint:
            raise FoundryDemoError("PROJECT_ENDPOINT is required.")

        template = self._get_selected_template()
        if template is None:
            raise FoundryDemoError("No industry template selected.")

        models = self._get_selected_models()
        if not (MIN_SELECTED_MODELS <= len(models) <= MAX_SELECTED_MODELS):
            raise FoundryDemoError(f"Select {MIN_SELECTED_MODELS}-{MAX_SELECTED_MODELS} models (got {len(models)}).")

        total_agents_raw = self.query_one("#total_agents", Input).value.strip()
        try:
            total_agents = int(total_agents_raw)
        except ValueError as exc:
            raise FoundryDemoError(f"Invalid total_agents: {total_agents_raw!r}") from exc
        org_id_raw = self.query_one("#org_id", Input).value.strip()
        org_id = org_id_raw or None

        seed_raw = self.query_one("#seed", Input).value.strip()
        if seed_raw:
            try:
                seed = int(seed_raw)
            except ValueError as exc:
                raise FoundryDemoError(f"Invalid seed: {seed_raw!r}") from exc
        else:
            seed = None

        include_daemon = bool(self.query_one("#include_daemon", Checkbox).value)
        create_now = bool(self.query_one("#create_now", Checkbox).value)

        agents = generate_agents(template=template, total_agents=total_agents, models=models, org_id=org_id, seed=seed)

        workspace_name = self.query_one("#workspace_name", Input).value.strip() or None
        workspace = create_workspace(DEFAULT_WORKSPACES_DIR, name=workspace_name)
        self._generated_workspace = workspace

        (workspace / ".env").write_text(f"PROJECT_ENDPOINT={endpoint}\n", encoding="utf-8")
        write_selected_models(workspace, models)
        write_generated_agents(workspace, agents)

        artifacts = generate_workspace(output_dir=workspace, template=template, agents=agents, include_daemon=include_daemon)

        if create_now:
            self._set_status("Creating agents in Foundry (this can take a few minutes)...")
            self.run_worker(
                lambda: self._create_agents_worker(endpoint=endpoint, agents=agents, workspace=workspace),
                exclusive=True,
                thread=True,
            )
            return

        self._set_status(self._workspace_summary(workspace, artifacts))

    def _create_agents_worker(self, *, endpoint: str, agents, workspace: Path) -> None:  # type: ignore[no-untyped-def]
        try:
            from .azure_ops import FoundryProject

            project = FoundryProject(endpoint=endpoint)
            created, failed = project.create_agents(agents=agents)
            write_created_agents_csv(workspace / "created_agents_results.csv", created)
            if failed:
                write_failed_agents_csv(workspace / "failed_agents_results.csv", failed)
            self.call_from_thread(
                self._set_status,
                f"Created {len(created)} agents, failed {len(failed)}. Workspace: {workspace}\n"
                f"Next: run `python {workspace}/simulate_agent_operations.py`",
            )
        except MissingDependencyError as exc:
            self.call_from_thread(self._set_status, str(exc))
        except Exception as exc:  # noqa: BLE001
            self.call_from_thread(self._set_status, f"Agent creation failed: {exc}")

    def _get_selected_models(self) -> list[str]:
        models_list = self.query_one("#models_list", SelectionList)
        selected = [str(v).strip() for v in models_list.selected if str(v).strip()]
        if selected:
            return selected

        manual = self.query_one("#manual_models", Input).value
        return [m.strip() for m in manual.split(",") if m.strip()]

    def _get_selected_template(self):
        if not self._templates:
            return None
        select = self.query_one("#industry_select", Select)
        template_id = select.value
        if template_id in (Select.BLANK, None):
            return None
        return self._template_by_id.get(str(template_id))

    def _update_industry_details(self) -> None:
        details = self.query_one("#industry_details", Static)
        template = self._get_selected_template()
        if template is None:
            details.update("No templates found. Add YAML files under `industry_templates/`.")
            return
        archetypes = template.archetypes
        preview = "\n".join([f"- {a.agent_type}: {a.display_name} ({a.owner})" for a in archetypes[:12]])
        if len(archetypes) > 12:
            preview += f"\n… ({len(archetypes) - 12} more)"
        details.update(
            f"Template: {template.display_name} ({template.template_id})\n"
            f"Default org: {template.default_org_id}\n"
            f"Archetypes: {len(archetypes)}\n\n"
            f"{preview}"
        )

    def _workspace_summary(self, workspace: Path, artifacts: dict[str, Path]) -> str:
        # Keep it short; the README_GENERATED.md inside the workspace has full instructions.
        lines = [
            f"Workspace generated: {workspace}",
            f"- Agents spec: {artifacts['agents_spec'].name}",
            f"- Create agents: {artifacts['create_agents'].name}",
            f"- Operations: {artifacts['operations'].name}",
            f"- Guardrails: {artifacts['guardrails'].name}",
            f"- README: {artifacts['readme'].name}",
        ]
        if "daemon" in artifacts:
            lines.append(f"- Daemon: {artifacts['daemon'].name} (manager: {artifacts['daemon_manager'].name})")
        lines.append("")
        lines.append("Next steps (inside the workspace):")
        lines.append("  1) python create_agents.py --spec agents_spec.csv")
        lines.append("  2) python simulate_agent_operations.py --num-calls 100")
        return "\n".join(lines)

    def _set_status(self, message: str) -> None:
        self.query_one("#status", Static).update(message)


def main() -> None:  # pragma: no cover
    FoundryDemoTUI().run()


if __name__ == "__main__":  # pragma: no cover
    main()
