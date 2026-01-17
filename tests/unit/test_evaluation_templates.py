from pathlib import Path

import pytest

from src.core.evaluation_templates import EvaluationTemplateLoader


@pytest.mark.unit
def test_evaluation_template_loader(tmp_path: Path):
    template_path = tmp_path / "basic.yaml"
    template_path.write_text(
        """
id: basic

display_name: Basic Eval

description: Simple template

dataset:
  items:
    - query: "Hello"
      context: "Context"
      ground_truth: "Hi"

evaluators:
  - name: Relevance
    type: relevance
    initialization_parameters:
      deployment_name: gpt-4o
""".lstrip(),
        encoding="utf-8",
    )

    loader = EvaluationTemplateLoader(templates_dir=tmp_path)
    template = loader.load_template("basic")

    assert template.id == "basic"
    assert template.display_name == "Basic Eval"
    assert template.dataset_items[0].query == "Hello"
    assert template.evaluators[0].name == "Relevance"
