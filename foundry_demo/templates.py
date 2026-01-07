from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from .errors import FoundryDemoError, MissingDependencyError
from .types import AgentArchetype, IndustryTemplate


def _require_yaml() -> Any:
    try:
        import yaml  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise MissingDependencyError(
            "Missing dependency: PyYAML. Install with `pip install pyyaml`."
        ) from exc
    return yaml


def load_industry_template(path: Path) -> IndustryTemplate:
    if not path.exists():
        raise FoundryDemoError(f"Template not found: {path}")

    yaml = _require_yaml()
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise FoundryDemoError(f"Invalid template YAML (expected mapping): {path}")

    template_id = str(data.get("id", "")).strip()
    display_name = str(data.get("name", "")).strip()
    default_org_id = str(data.get("default_org_id", "ORG01")).strip() or "ORG01"

    archetypes_raw = data.get("agent_archetypes", [])
    if not isinstance(archetypes_raw, list) or not archetypes_raw:
        raise FoundryDemoError(f"Template has no agent_archetypes: {path}")

    archetypes: list[AgentArchetype] = []
    for idx, item in enumerate(archetypes_raw):
        if not isinstance(item, dict):
            raise FoundryDemoError(f"Invalid agent_archetypes[{idx}] in {path}")
        archetypes.append(
            AgentArchetype(
                agent_type=str(item.get("agent_type", "")).strip(),
                display_name=str(item.get("display_name", "")).strip()
                or str(item.get("agent_type", "")).strip(),
                owner=str(item.get("owner", "")).strip(),
                purpose=str(item.get("purpose", "")).strip(),
                tools=str(item.get("tools", "")).strip(),
                query_templates=[str(q) for q in (item.get("query_templates", []) or [])],
            )
        )

    if not template_id:
        raise FoundryDemoError(f"Template missing `id`: {path}")
    if not display_name:
        raise FoundryDemoError(f"Template missing `name`: {path}")
    if any(not a.agent_type for a in archetypes):
        raise FoundryDemoError(f"Template has archetype with empty agent_type: {path}")

    return IndustryTemplate(
        template_id=template_id,
        display_name=display_name,
        default_org_id=default_org_id,
        archetypes=archetypes,
        raw=data,
    )


def list_industry_templates(templates_dir: Path) -> list[IndustryTemplate]:
    if not templates_dir.exists():
        return []
    templates: list[IndustryTemplate] = []
    for path in sorted(templates_dir.glob("*.y*ml")):
        templates.append(load_industry_template(path))
    return templates


def template_to_dict(template: IndustryTemplate) -> dict[str, Any]:
    return {
        "id": template.template_id,
        "name": template.display_name,
        "default_org_id": template.default_org_id,
        "agent_archetypes": [asdict(a) for a in template.archetypes],
    }

