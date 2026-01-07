from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Optional

from .types import GeneratedAgent


def create_workspace(base_dir: Path, *, name: Optional[str] = None) -> Path:
    base_dir.mkdir(parents=True, exist_ok=True)
    if name is None:
        name = datetime.now().strftime("%Y%m%d-%H%M%S")
    candidate = base_dir / name
    if not candidate.exists():
        candidate.mkdir(parents=True, exist_ok=False)
        return candidate

    # Avoid overwriting an existing workspace.
    for i in range(1, 1000):
        candidate = base_dir / f"{name}-{i}"
        if not candidate.exists():
            candidate.mkdir(parents=True, exist_ok=False)
            return candidate

    raise RuntimeError(f"Unable to create a unique workspace under {base_dir} for base name '{name}'")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_selected_models(workspace: Path, models: list[str]) -> Path:
    out = workspace / "selected_models.json"
    write_json(out, {"models": models})
    return out


def write_generated_agents(workspace: Path, agents: Iterable[GeneratedAgent]) -> Path:
    out = workspace / "generated_agents.json"
    write_json(out, {"agents": [asdict(a) for a in agents]})
    return out
