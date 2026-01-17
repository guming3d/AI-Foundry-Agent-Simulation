import pytest

from src.core.metrics_collector import MetricsCollector, OperationMetric, GuardrailMetric


@pytest.mark.unit
def test_operation_summary_counts():
    collector = MetricsCollector()
    collector.start()

    collector.add_operation_metric(
        OperationMetric(
            timestamp="2024-01-01T00:00:00",
            agent_id="AG001",
            agent_name="ORG-Agent-AG001",
            azure_id="azure-1",
            model="model-a",
            org_id="ORG001",
            agent_type="Agent",
            query="hello",
            query_length=5,
            response_text="hi",
            response_length=2,
            latency_ms=100.0,
            success=True,
        )
    )
    collector.add_operation_metric(
        OperationMetric(
            timestamp="2024-01-01T00:00:01",
            agent_id="AG002",
            agent_name="ORG-Agent-AG002",
            azure_id="azure-2",
            model="model-b",
            org_id="ORG001",
            agent_type="Agent",
            query="hello",
            query_length=5,
            response_text=None,
            response_length=0,
            latency_ms=200.0,
            success=False,
            error_message="timeout",
        )
    )
    collector.stop()

    summary = collector.get_operation_summary()

    assert summary["total_calls"] == 2
    assert summary["successful_calls"] == 1
    assert summary["failed_calls"] == 1
    assert summary["agent_type_distribution"]["Agent"] == 2


@pytest.mark.unit
def test_guardrail_summary_counts():
    collector = MetricsCollector()
    collector.start()

    collector.add_guardrail_metric(
        GuardrailMetric(
            timestamp="2024-01-01T00:00:00",
            agent_id="AG001",
            agent_name="ORG-Agent-AG001",
            azure_id="azure-1",
            model="model-a",
            org_id="ORG001",
            test_category="harm",
            test_query="test",
            query_length=4,
            response_text="refuse",
            response_length=6,
            latency_ms=120.0,
            blocked=True,
            content_filter_triggered=False,
            error_message=None,
            guardrail_status="PASS",
        )
    )
    collector.add_guardrail_metric(
        GuardrailMetric(
            timestamp="2024-01-01T00:00:01",
            agent_id="AG002",
            agent_name="ORG-Agent-AG002",
            azure_id="azure-2",
            model="model-a",
            org_id="ORG001",
            test_category="harm",
            test_query="test",
            query_length=4,
            response_text="ok",
            response_length=2,
            latency_ms=110.0,
            blocked=False,
            content_filter_triggered=False,
            error_message=None,
            guardrail_status="FAIL",
        )
    )
    collector.stop()

    summary = collector.get_guardrail_summary()

    assert summary["total_tests"] == 2
    assert summary["blocked"] == 1
    assert summary["allowed"] == 1
    assert summary["category_stats"]["harm"]["total"] == 2
