import csv

import pytest

from src.core.agent_manager import AgentManager


@pytest.mark.unit
def test_save_failed_to_csv_includes_context_columns(tmp_path):
    output_path = tmp_path / "failed.csv"
    failed = [
        {
            "agent_id": "AG001",
            "name": "ORG-Agent-AG001",
            "org_id": "ORG001",
            "agent_type": "Agent",
            "error": "boom",
            "extra": "ignored",
        }
    ]

    manager = AgentManager(models=["gpt-4o"])
    manager.save_failed_to_csv(failed, output_path=str(output_path))

    with open(output_path, "r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    assert reader.fieldnames == ["agent_id", "name", "org_id", "agent_type", "error"]
    assert rows[0]["org_id"] == "ORG001"
    assert rows[0]["agent_type"] == "Agent"
