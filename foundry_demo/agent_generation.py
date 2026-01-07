from __future__ import annotations

import csv
import random
from pathlib import Path
from typing import Iterable, Optional

from .errors import FoundryDemoError
from .types import GeneratedAgent, IndustryTemplate


def _clean_type(agent_type: str) -> str:
    return "".join(ch for ch in agent_type.strip() if ch.isalnum() or ch in ("_", "-")).replace(" ", "")


def generate_agents(
    *,
    template: IndustryTemplate,
    total_agents: int,
    models: list[str],
    org_id: Optional[str] = None,
    seed: Optional[int] = None,
) -> list[GeneratedAgent]:
    if total_agents <= 0:
        raise FoundryDemoError("total_agents must be > 0")
    if not models:
        raise FoundryDemoError("models must be non-empty")

    rng = random.Random(seed)
    org_id_value = (org_id or template.default_org_id or "ORG01").strip() or "ORG01"

    archetypes = template.archetypes
    if total_agents <= len(archetypes):
        chosen = rng.sample(archetypes, k=total_agents)
    else:
        chosen = []
        full_sets = total_agents // len(archetypes)
        remainder = total_agents % len(archetypes)
        for _ in range(full_sets):
            chosen.extend(archetypes)
        chosen.extend(rng.sample(archetypes, k=remainder))
        rng.shuffle(chosen)

    generated: list[GeneratedAgent] = []
    for idx, archetype in enumerate(chosen, start=1):
        agent_id = f"AG{idx:03d}"
        agent_type = _clean_type(archetype.agent_type)
        name = f"{org_id_value}-{agent_type}-{agent_id}"
        model = rng.choice(models).strip()
        generated.append(
            GeneratedAgent(
                agent_id=agent_id,
                org_id=org_id_value,
                agent_type=agent_type,
                name=name,
                owner=archetype.owner,
                purpose=archetype.purpose,
                tools=archetype.tools,
                model=model,
            )
        )
    return generated


def write_agents_spec_csv(agents: Iterable[GeneratedAgent], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["agent_id", "org_id", "agent_type", "name", "owner", "purpose", "tools", "model"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for agent in agents:
            writer.writerow(
                {
                    "agent_id": agent.agent_id,
                    "org_id": agent.org_id,
                    "agent_type": agent.agent_type,
                    "name": agent.name,
                    "owner": agent.owner,
                    "purpose": agent.purpose,
                    "tools": agent.tools,
                    "model": agent.model,
                }
            )

