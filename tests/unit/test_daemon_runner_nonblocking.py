import time

from src.core.daemon_runner import DaemonRunner, DaemonConfig
from src.models.agent import CreatedAgent


def _dummy_agent() -> CreatedAgent:
    return CreatedAgent(
        agent_id="AG001",
        name="ORG-TestAgent-AG001",
        azure_id="ORG-TestAgent-AG001:1",
        version=1,
        model="gpt-test",
        org_id="ORG",
        agent_type="TestAgent",
    )


def test_daemon_scheduler_does_not_block_on_slow_calls(monkeypatch) -> None:
    runner = DaemonRunner(agents=[_dummy_agent()])

    monkeypatch.setattr(runner, "_get_openai_client", lambda: object())

    def slow_call_agent(_agent, _query, _openai_client):
        time.sleep(5.0)
        return {
            "response_text": "ok",
            "response_length": 2,
            "latency_ms": 5000.0,
            "success": True,
            "error_message": None,
        }

    monkeypatch.setattr(runner, "_call_agent", slow_call_agent)

    config = DaemonConfig(
        interval_seconds=0.5,
        calls_per_batch_min=4,
        calls_per_batch_max=4,
        threads=1,
        delay=0.0,
        operations_weight=100,
        queue_maxsize=100,
        overload_policy="drop",
        log_each_call=False,
    )

    assert runner.start(config, log_callback=lambda _msg: None, metrics_callback=lambda _m: None)
    time.sleep(1.3)

    metrics = runner.get_metrics()
    assert metrics["batches_completed"] >= 2
    assert metrics["scheduled_calls"] >= 6
    assert metrics["queue_depth"] >= 1

    runner.request_stop()
    runner.stop()


def test_daemon_overload_drops_when_queue_full(monkeypatch) -> None:
    runner = DaemonRunner(agents=[_dummy_agent()])

    monkeypatch.setattr(runner, "_get_openai_client", lambda: object())

    def slow_call_agent(_agent, _query, _openai_client):
        time.sleep(5.0)
        return {
            "response_text": "ok",
            "response_length": 2,
            "latency_ms": 5000.0,
            "success": True,
            "error_message": None,
        }

    monkeypatch.setattr(runner, "_call_agent", slow_call_agent)

    config = DaemonConfig(
        interval_seconds=0.5,
        calls_per_batch_min=10,
        calls_per_batch_max=10,
        threads=1,
        delay=0.0,
        operations_weight=100,
        queue_maxsize=1,
        overload_policy="drop",
        log_each_call=False,
    )

    assert runner.start(config, log_callback=lambda _msg: None, metrics_callback=lambda _m: None)
    time.sleep(1.0)

    metrics = runner.get_metrics()
    assert metrics["dropped_calls"] > 0
    assert metrics["scheduled_calls"] > metrics["queue_depth"]

    runner.request_stop()
    runner.stop()

