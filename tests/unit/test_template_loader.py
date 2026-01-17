from pathlib import Path

import pytest

from src.templates.template_loader import TemplateLoader


@pytest.mark.unit
def test_template_loader_parses_profile(tmp_path: Path):
    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    template_path = template_dir / "sample.yaml"
    template_path.write_text(
        """
metadata:
  id: sample
  name: Sample Profile
organization:
  prefix: ORG
  departments:
    - name: Support
      code: SUP
models:
  preferred:
    - gpt-4o
  allowed:
    - gpt-4o
agent_types:
  - id: SupportAgent
    name: Support Agent
    department: SUP
    description: Helps customers
    instructions: Be helpful
    tools:
      - search
    query_templates:
      - "Help me with {}"
""".lstrip(),
        encoding="utf-8",
    )

    loader = TemplateLoader(templates_dir=str(template_dir))
    templates = loader.list_templates()

    assert templates == ["sample"]

    profile = loader.load_template("sample")
    assert profile.metadata.id == "sample"
    assert profile.organization.prefix == "ORG"
    assert profile.agent_types[0].id == "SupportAgent"
