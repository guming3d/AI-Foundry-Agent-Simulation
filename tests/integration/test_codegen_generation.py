from pathlib import Path

import pytest

from src.codegen.generator import generate_code_for_profile
from src.templates.template_loader import TemplateLoader


@pytest.mark.integration
def test_generate_code_outputs_files(tmp_path: Path):
    loader = TemplateLoader()
    profile = loader.load_template(loader.list_templates()[0])

    output_dir = tmp_path / "generated"
    results = generate_code_for_profile(
        profile=profile,
        output_dir=str(output_dir),
        agents_csv="agents.csv",
        endpoint="https://example.services.ai.azure.com/api/projects/example",
    )

    expected_files = {
        "simulate_agent_operations.py",
        "simulate_guardrail_testing.py",
        "simulation_daemon_config.json",
    }

    assert set(results.keys()) == expected_files
    for filename, path in results.items():
        assert Path(path).exists()
        assert Path(path).read_text(encoding="utf-8").strip()
