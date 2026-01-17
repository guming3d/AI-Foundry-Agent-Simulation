import os

import pytest

from src.core.env_validator import EnvValidator


@pytest.mark.unit
def test_validate_missing_env(monkeypatch):
    monkeypatch.delenv("PROJECT_ENDPOINT", raising=False)
    result = EnvValidator.validate()
    assert result.is_valid is False
    assert "PROJECT_ENDPOINT" in result.missing_vars


@pytest.mark.unit
def test_update_env_file_writes_endpoint(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    example_file = tmp_path / ".env.example"

    monkeypatch.setattr(EnvValidator, "ENV_FILE", env_file)
    monkeypatch.setattr(EnvValidator, "ENV_EXAMPLE_FILE", example_file)
    monkeypatch.setattr(EnvValidator, "reload_environment", lambda: None)
    monkeypatch.setattr(EnvValidator, "_update_azure_client", lambda endpoint: None)

    monkeypatch.delenv("PROJECT_ENDPOINT", raising=False)
    endpoint = "https://example.services.ai.azure.com/api/projects/example"

    success, message = EnvValidator.update_env_file(endpoint)

    assert success is True
    assert env_file.read_text(encoding="utf-8").strip() == f"PROJECT_ENDPOINT={endpoint}"
    assert os.environ.get("PROJECT_ENDPOINT") == endpoint
    assert "Successfully updated" in message
