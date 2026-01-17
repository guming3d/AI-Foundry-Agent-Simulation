"""
Sample evaluation template loader.

Loads YAML-based evaluation templates used to run local sample evaluations.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

import yaml


@dataclass
class EvaluationItem:
    """Single evaluation dataset row."""

    query: str
    context: str = ""
    ground_truth: str = ""


@dataclass
class EvaluatorDefinition:
    """Evaluator definition for a template."""

    name: str
    type: str
    evaluator_id: str = ""
    min_score: float = 0.0
    init_params: Dict[str, Any] = field(default_factory=dict)
    data_mapping: Dict[str, Any] = field(default_factory=dict)
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvaluationTemplate:
    """Evaluation template metadata and dataset."""

    id: str
    display_name: str
    description: str
    dataset_items: List[EvaluationItem] = field(default_factory=list)
    evaluators: List[EvaluatorDefinition] = field(default_factory=list)


class EvaluationTemplateLoader:
    """Loader for YAML-based evaluation templates."""

    def __init__(self, templates_dir: Path = None) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        self.templates_dir = templates_dir or repo_root / "evaluation-templates"

    def list_template_files(self) -> List[Path]:
        """List available template files."""
        return sorted(self.templates_dir.glob("*.yaml"))

    def list_templates(self) -> List[EvaluationTemplate]:
        """Load all templates."""
        templates = []
        for path in self.list_template_files():
            templates.append(self._load_from_path(path))
        return templates

    def load_template(self, template_id: str) -> EvaluationTemplate:
        """Load a template by ID."""
        for path in self.list_template_files():
            if path.stem == template_id:
                return self._load_from_path(path)
        raise FileNotFoundError(f"Evaluation template '{template_id}' not found")

    def _load_from_path(self, path: Path) -> EvaluationTemplate:
        """Load a template from a YAML file."""
        with open(path, "r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}

        template_id = data.get("id", "").strip()
        if not template_id:
            raise ValueError(f"Template '{path.name}' is missing an id")

        display_name = data.get("display_name", "").strip()
        description = data.get("description", "").strip()

        dataset_items = []
        dataset_data = data.get("dataset", {}) or {}
        for item in dataset_data.get("items", []) or []:
            dataset_items.append(
                EvaluationItem(
                    query=str(item.get("query", "")).strip(),
                    context=str(item.get("context", "") or "").strip(),
                    ground_truth=str(item.get("ground_truth", "") or "").strip(),
                )
            )

        evaluators = []
        for evaluator in data.get("evaluators", []) or []:
            evaluators.append(
                EvaluatorDefinition(
                    name=str(evaluator.get("name", "")).strip(),
                    type=str(evaluator.get("type", "")).strip(),
                    evaluator_id=str(evaluator.get("evaluator_id", "")).strip(),
                    min_score=float(evaluator.get("min_score", 0.0) or 0.0),
                    init_params=dict(
                        evaluator.get("initialization_parameters")
                        or evaluator.get("init_params", {})
                        or {}
                    ),
                    data_mapping=dict(evaluator.get("data_mapping", {}) or {}),
                    params=dict(evaluator.get("params", {}) or {}),
                )
            )

        return EvaluationTemplate(
            id=template_id,
            display_name=display_name or template_id,
            description=description,
            dataset_items=dataset_items,
            evaluators=evaluators,
        )
