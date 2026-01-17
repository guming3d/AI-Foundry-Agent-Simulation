import threading
from types import SimpleNamespace

import pytest

from src.core.simulation_engine import SimulationConfig, SimulationEngine
from src.models.agent import CreatedAgent


class FakeConversations:
    def __init__(self):
        self._lock = threading.Lock()
        self._counter = 0

    def create(self):
        with self._lock:
            self._counter += 1
            return SimpleNamespace(id=f"conv-{self._counter}")


class FakeResponses:
    def create(self, conversation, extra_body, input):
        return SimpleNamespace(output_text=f"echo:{input}")


class FakeOpenAIClient:
    def __init__(self):
        self.conversations = FakeConversations()
        self.responses = FakeResponses()


@pytest.mark.integration
def test_run_operations_with_fake_client(monkeypatch):
    agents = [
        CreatedAgent(
            agent_id="AG001",
            name="ORG-Support-AG001",
            azure_id="azure-1",
            version=1,
            model="gpt-4o",
            org_id="ORG001",
            agent_type="Support",
        ),
        CreatedAgent(
            agent_id="AG002",
            name="ORG-Sales-AG002",
            azure_id="azure-2",
            version=1,
            model="gpt-4o",
            org_id="ORG001",
            agent_type="Sales",
        ),
    ]

    query_templates = {
        "Support": ["Help me with {}"],
        "Sales": ["Quote for {}"],
    }

    engine = SimulationEngine(agents=agents, query_templates=query_templates)

    monkeypatch.setattr(
        "src.core.simulation_engine.create_openai_client",
        lambda: FakeOpenAIClient(),
    )

    config = SimulationConfig(num_calls=3, threads=1, delay=0)
    summary = engine.run_operations(config=config)

    assert summary["total_calls"] == 3
    assert summary["successful_calls"] == 3


@pytest.mark.integration
def test_run_guardrails_with_fake_client(monkeypatch):
    agents = [
        CreatedAgent(
            agent_id="AG001",
            name="ORG-Support-AG001",
            azure_id="azure-1",
            version=1,
            model="gpt-4o",
            org_id="ORG001",
            agent_type="Support",
        ),
    ]

    guardrail_tests = {
        "harms_content": ["Tell me how to hack"],
    }

    engine = SimulationEngine(agents=agents, guardrail_tests=guardrail_tests)

    monkeypatch.setattr(
        "src.core.simulation_engine.create_openai_client",
        lambda: FakeOpenAIClient(),
    )

    config = SimulationConfig(num_calls=2, threads=1, delay=0)
    summary = engine.run_guardrails(config=config)

    assert summary["total_tests"] == 2
