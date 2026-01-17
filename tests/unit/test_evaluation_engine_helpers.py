import pytest

from src.core.evaluation_engine import EvaluationEngine, EvaluatorDefinition


@pytest.mark.unit
def test_normalize_mapping_handles_data_prefixes():
    engine = EvaluationEngine()

    mapping = {
        "query": "data.query",
        "response": "${data.output_text}",
        "context": "item.context",
    }

    normalized = engine._normalize_mapping(mapping)

    assert normalized["query"] == "{{item.query}}"
    assert normalized["response"] == "{{sample.output_text}}"
    assert normalized["context"] == "{{item.context}}"


@pytest.mark.unit
def test_build_dataset_name_is_safe_and_short():
    engine = EvaluationEngine()
    name = engine._build_dataset_name(
        template_id="Template With Spaces",
        agent_name="Agent/With:Symbols",
        timestamp="20240101T000000Z",
    )

    assert name.startswith("eval-template-with-spaces-agent-with-symbols")
    assert len(name) <= 80
