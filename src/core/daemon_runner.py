"""
Daemon runner for continuous production traffic simulation.

Provides a background daemon that simulates realistic user traffic
patterns to AI agents for testing and demonstration purposes.
"""

import csv
import os
import random
import time
import threading
from collections import deque
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from queue import Queue, Empty, Full

from .azure_client import create_openai_client
from .metrics_collector import MetricsCollector, OperationMetric, GuardrailMetric
from ..models.agent import CreatedAgent
from ..models.industry_profile import IndustryProfile


@dataclass
class DaemonConfig:
    """Configuration for daemon simulation."""
    interval_seconds: int = 60  # Duration of each scheduling window
    calls_per_batch_min: int = 5
    calls_per_batch_max: int = 15
    threads: int = 3
    delay: float = 0.5
    operations_weight: int = 80  # Percentage of operations vs guardrails
    # Randomly vary the batch size around the selected traffic rate to simulate burstiness.
    # Example: 20 means calls_per_batch_min/max will vary by +/-20% from the base.
    traffic_variance_pct: int = 20
    # Backward compat: older daemon state may still include this field.
    load_profile_override: str = "auto"
    output_dir: str = "daemon_results"
    # Benchmarking controls.
    queue_maxsize: int = 0  # 0 => auto derived from target rate/threads
    overload_policy: str = "drop"  # "drop" (default) or "block"
    drain_on_stop: bool = False
    schedule_jitter_seconds: float = 0.0  # Small random jitter per call start
    log_each_call: bool = True  # Disable to reduce IO overhead at high rates
    log_sample_every: int = 1  # Log every Nth completed call when log_each_call is True
    latency_sample_size: int = 1000  # Rolling window for percentile estimates


@dataclass
class DaemonMetrics:
    """Live metrics for daemon monitoring."""
    total_calls: int = 0
    scheduled_calls: int = 0
    started_calls: int = 0
    dropped_calls: int = 0
    inflight_calls: int = 0
    queue_depth: int = 0
    target_calls_per_minute: float = 0.0
    successful_calls: int = 0
    failed_calls: int = 0
    total_operations: int = 0
    total_guardrails: int = 0
    blocked_guardrails: int = 0
    total_latency_ms: float = 0
    max_latency_ms: float = 0
    batches_completed: int = 0
    start_time: Optional[datetime] = None
    last_batch_time: Optional[datetime] = None
    current_load_profile: str = "normal"
    errors: List[str] = field(default_factory=list)
    latency_samples_ms: deque[float] = field(default_factory=lambda: deque(maxlen=1000))

    def get_success_rate(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return (self.successful_calls / self.total_calls) * 100

    def get_avg_latency(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.total_latency_ms / self.total_calls

    def get_calls_per_minute(self) -> float:
        if self.start_time is None:
            return 0.0
        elapsed = (datetime.now() - self.start_time).total_seconds()
        if elapsed < 60:
            return self.total_calls
        return (self.total_calls / elapsed) * 60

    def get_started_calls_per_minute(self) -> float:
        if self.start_time is None:
            return 0.0
        elapsed = (datetime.now() - self.start_time).total_seconds()
        if elapsed < 60:
            return self.started_calls
        return (self.started_calls / elapsed) * 60

    def _get_latency_percentile_ms(self, percentile: float) -> float:
        if not self.latency_samples_ms:
            return 0.0
        samples = sorted(self.latency_samples_ms)
        percentile = max(0.0, min(100.0, float(percentile)))
        idx = int(round((percentile / 100.0) * (len(samples) - 1)))
        return float(samples[idx])

    def get_runtime(self) -> str:
        if self.start_time is None:
            return "0s"
        elapsed = (datetime.now() - self.start_time).total_seconds()
        hours = int(elapsed // 3600)
        minutes = int((elapsed % 3600) // 60)
        seconds = int(elapsed % 60)
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        return f"{seconds}s"

    def to_dict(self) -> Dict[str, Any]:
        # Keep `current_load_profile` for older UI versions; newer UI should use `traffic_variance`.
        return {
            "total_calls": self.total_calls,
            "scheduled_calls": self.scheduled_calls,
            "started_calls": self.started_calls,
            "dropped_calls": self.dropped_calls,
            "inflight_calls": self.inflight_calls,
            "queue_depth": self.queue_depth,
            "target_calls_per_minute": round(self.target_calls_per_minute, 1),
            "successful_calls": self.successful_calls,
            "failed_calls": self.failed_calls,
            "success_rate": round(self.get_success_rate(), 1),
            "total_operations": self.total_operations,
            "total_guardrails": self.total_guardrails,
            "blocked_guardrails": self.blocked_guardrails,
            "avg_latency_ms": round(self.get_avg_latency(), 1),
            "p50_latency_ms": round(self._get_latency_percentile_ms(50), 1),
            "p95_latency_ms": round(self._get_latency_percentile_ms(95), 1),
            "max_latency_ms": round(self.max_latency_ms, 1),
            "calls_per_minute": round(self.get_calls_per_minute(), 1),
            "started_calls_per_minute": round(self.get_started_calls_per_minute(), 1),
            "batches_completed": self.batches_completed,
            "runtime": self.get_runtime(),
            "current_load_profile": self.current_load_profile,
            "traffic_variance": self.current_load_profile,
            "recent_errors": self.errors[-5:] if self.errors else [],
        }


class DaemonRunner:
    """
    Continuous simulation daemon for production traffic simulation.

    Runs in the background and simulates realistic user traffic patterns
    to AI agents, collecting metrics for monitoring and analysis.
    """

    # Blocking indicators for guardrail detection
    BLOCKING_INDICATORS = [
        "i cannot", "i can't", "i won't", "i am not able",
        "unable to", "cannot assist", "not appropriate",
        "against my guidelines", "ethical guidelines",
        "not permitted", "inappropriate", "harmful",
        "illegal", "refuse", "decline",
    ]

    def __init__(
        self,
        agents: Optional[List[CreatedAgent]] = None,
        agents_csv: str = "created_agents_results.csv",
        profile: Optional[IndustryProfile] = None,
    ):
        """
        Initialize the daemon runner.

        Args:
            agents: Optional list of agents to use (preferred over CSV)
            agents_csv: Path to the agents CSV file
            profile: Optional industry profile for query templates
        """
        self.agents_csv = agents_csv
        self.profile = profile
        self.agents: List[CreatedAgent] = agents or []
        self.query_templates: Dict[str, List[str]] = {}
        self.guardrail_tests: Dict[str, List[str]] = {}

        self._is_running = False
        self._stop_requested = False
        self._daemon_thread: Optional[threading.Thread] = None
        self._metrics = DaemonMetrics()
        self._metrics_lock = threading.Lock()
        self._log_callback: Optional[Callable[[str], None]] = None
        self._metrics_callback: Optional[Callable[[Dict], None]] = None
        self._metrics_history: List[Dict[str, Any]] = []
        self._metrics_history_max = 240
        self._output_dir: Optional[str] = None
        self._metrics_flush_interval = 5.0
        self._last_metrics_flush = 0.0
        self._metrics_flusher_thread: Optional[threading.Thread] = None
        self._thread_local = threading.local()
        self._log_lock = threading.Lock()
        self._flush_lock = threading.Lock()
        self._task_queue: Optional[Queue] = None
        self._workers: List[threading.Thread] = []
        self._scheduler_thread: Optional[threading.Thread] = None
        self._active_config: DaemonConfig = DaemonConfig()

        # Load agents from CSV only if none provided
        if not self.agents:
            self._load_agents()

        # Load templates from profile
        if profile:
            self.query_templates = profile.get_query_templates_dict()
            self.guardrail_tests = profile.guardrail_tests.get_non_empty_categories()

    def _load_agents(self) -> None:
        """Load agents from CSV file."""
        if not os.path.exists(self.agents_csv):
            return

        self.agents = []
        with open(self.agents_csv, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.agents.append(CreatedAgent.from_csv_row(row))

    def _get_batch_size(self, config: DaemonConfig) -> int:
        """Get batch size with bounded randomness."""
        min_calls = max(1, int(config.calls_per_batch_min))
        max_calls = max(min_calls, int(config.calls_per_batch_max))
        return random.randint(min_calls, max_calls)

    def _extract_agent_type(self, agent_name: str) -> str:
        """Extract agent type from agent name."""
        parts = agent_name.split('-')
        if len(parts) >= 2:
            return parts[1]
        return "Unknown"

    def _generate_query(self, agent_type: str) -> str:
        """Generate a query for the given agent type."""
        if agent_type not in self.query_templates:
            return "Can you help me with my request?"

        template = random.choice(self.query_templates[agent_type])

        if '{}' in template:
            placeholders = template.count('{}')
            random_values = [str(random.randint(1000, 9999)) for _ in range(placeholders)]
            return template.format(*random_values)

        return template

    def _generate_guardrail_query(self) -> tuple:
        """Generate a guardrail test query."""
        if not self.guardrail_tests:
            return None, "No test queries configured"

        categories = list(self.guardrail_tests.keys())
        if not categories:
            return None, "No test categories available"

        category = random.choice(categories)
        query = random.choice(self.guardrail_tests[category])
        return category, query

    def _is_blocked(self, response_text: str, error_message: str) -> tuple:
        """Determine if a guardrail test was blocked."""
        if error_message:
            error_lower = error_message.lower()
            if any(ind in error_lower for ind in ['content', 'filter', 'policy', 'safety', 'blocked']):
                return True, True

        if response_text:
            response_lower = response_text.lower()
            for indicator in self.BLOCKING_INDICATORS:
                if indicator in response_lower:
                    return True, False

        return False, False

    def _call_agent(self, agent: CreatedAgent, query: str, openai_client) -> Dict[str, Any]:
        """Call an agent and return the result."""
        start_time = time.time()
        success = False
        error_message = None
        response_text = None
        response_length = 0

        try:
            conversation = openai_client.conversations.create()
            response = openai_client.responses.create(
                conversation=conversation.id,
                extra_body={"agent": {"name": agent.name, "type": "agent_reference"}},
                input=query,
            )
            response_text = response.output_text
            response_length = len(response_text) if response_text else 0
            success = True

        except Exception as e:
            error_message = str(e)

        latency_ms = (time.time() - start_time) * 1000

        return {
            "response_text": response_text,
            "response_length": response_length,
            "latency_ms": round(latency_ms, 2),
            "success": success,
            "error_message": error_message,
        }

    def _get_openai_client(self):
        """Get a per-thread OpenAI client to avoid shared-client threading issues."""
        client = getattr(self._thread_local, "openai_client", None)
        if client is None:
            client = create_openai_client()
            self._thread_local.openai_client = client
        return client

    def _log(self, message: str) -> None:
        """Log a message through the callback."""
        if self._log_callback:
            with self._log_lock:
                self._log_callback(message)

    def _update_metrics(self, metrics_dict: Dict) -> None:
        """Update metrics through the callback."""
        if self._metrics_callback:
            self._metrics_callback(metrics_dict)
        self._maybe_flush_metrics()

    def _maybe_flush_metrics(self, force: bool = False) -> None:
        """Persist metrics periodically so the UI can refresh."""
        if not self._output_dir:
            return
        now = time.monotonic()
        if not (force or now - self._last_metrics_flush >= self._metrics_flush_interval):
            return
        with self._flush_lock:
            # Re-check under the lock to avoid overlapping writes from multiple worker threads.
            now = time.monotonic()
            if force or now - self._last_metrics_flush >= self._metrics_flush_interval:
                self._save_metrics(self._output_dir)
                self._last_metrics_flush = now

    def _execute_operation(self, agent: CreatedAgent) -> Dict[str, Any]:
        """Execute a single operation call."""
        openai_client = self._get_openai_client()
        agent_type = self._extract_agent_type(agent.name)
        query = self._generate_query(agent_type)
        result = self._call_agent(agent, query, openai_client)
        return {"type": "operation", "agent": agent, "result": result}

    def _execute_guardrail(self, agent: CreatedAgent) -> Dict[str, Any]:
        """Execute a single guardrail call."""
        openai_client = self._get_openai_client()
        category, query = self._generate_guardrail_query()
        if query is None:
            return {"type": "guardrail", "agent": agent, "result": None, "category": None}
        result = self._call_agent(agent, query, openai_client)
        blocked, _ = self._is_blocked(result["response_text"], result["error_message"])
        return {"type": "guardrail", "agent": agent, "result": result, "category": category, "blocked": blocked}

    def _process_operation_result(self, agent: CreatedAgent, result: Dict[str, Any]) -> None:
        """Process and record an operation result."""
        with self._metrics_lock:
            self._metrics.total_calls += 1
            self._metrics.total_operations += 1
            self._metrics.total_latency_ms += result["latency_ms"]
            self._metrics.max_latency_ms = max(self._metrics.max_latency_ms, float(result["latency_ms"]))
            self._metrics.latency_samples_ms.append(float(result["latency_ms"]))
            if result["success"]:
                self._metrics.successful_calls += 1
            else:
                self._metrics.failed_calls += 1
                if result["error_message"]:
                    self._metrics.errors.append(result["error_message"][:100])
                    self._metrics.errors = self._metrics.errors[-10:]

        status = "OK" if result["success"] else "FAIL"
        should_log = True
        if not getattr(self._active_config, "log_each_call", True):
            should_log = False
        else:
            sample_every = max(1, int(getattr(self._active_config, "log_sample_every", 1) or 1))
            with self._metrics_lock:
                should_log = (self._metrics.total_calls % sample_every) == 0
        if should_log:
            self._log(f"[OP] {agent.name}: {status} ({result['latency_ms']:.0f}ms)")

    def _process_guardrail_result(self, agent: CreatedAgent, result: Dict[str, Any], category: str, blocked: bool) -> None:
        """Process and record a guardrail result."""
        with self._metrics_lock:
            self._metrics.total_calls += 1
            self._metrics.total_guardrails += 1
            self._metrics.total_latency_ms += result["latency_ms"]
            self._metrics.max_latency_ms = max(self._metrics.max_latency_ms, float(result["latency_ms"]))
            self._metrics.latency_samples_ms.append(float(result["latency_ms"]))
            if result["success"]:
                self._metrics.successful_calls += 1
            else:
                self._metrics.failed_calls += 1
            if blocked:
                self._metrics.blocked_guardrails += 1

        status = "BLOCKED" if blocked else "ALLOWED"
        should_log = True
        if not getattr(self._active_config, "log_each_call", True):
            should_log = False
        else:
            sample_every = max(1, int(getattr(self._active_config, "log_sample_every", 1) or 1))
            with self._metrics_lock:
                should_log = (self._metrics.total_calls % sample_every) == 0
        if should_log:
            self._log(f"[GUARD] {agent.name} [{category}]: {status} ({result['latency_ms']:.0f}ms)")

    def _resolve_queue_maxsize(self, config: DaemonConfig) -> int:
        explicit = int(getattr(config, "queue_maxsize", 0) or 0)
        if explicit > 0:
            return explicit
        interval_calls = max(1, int(config.calls_per_batch_max))
        # Default: allow a few windows worth of work, and enough headroom to absorb slow tails.
        return max(interval_calls * 3, int(config.threads) * 10, 100)

    def _update_queue_metrics(self) -> None:
        if not self._task_queue:
            return
        with self._metrics_lock:
            self._metrics.queue_depth = int(self._task_queue.qsize() or 0)

    def _enqueue_task(self, task: Dict[str, Any], config: DaemonConfig) -> bool:
        if not self._task_queue:
            return False
        with self._metrics_lock:
            self._metrics.scheduled_calls += 1
        if config.overload_policy == "block":
            try:
                self._task_queue.put(task, timeout=1.0)
                self._update_queue_metrics()
                return True
            except Full:
                with self._metrics_lock:
                    self._metrics.dropped_calls += 1
                self._update_queue_metrics()
                return False
        try:
            self._task_queue.put_nowait(task)
            self._update_queue_metrics()
            return True
        except Full:
            with self._metrics_lock:
                self._metrics.dropped_calls += 1
            self._update_queue_metrics()
            return False

    def _scheduler_loop(self, config: DaemonConfig) -> None:
        """Schedule work in fixed windows without waiting for completion."""
        interval_s = max(1e-3, float(config.interval_seconds))
        jitter_s = max(0.0, float(getattr(config, "schedule_jitter_seconds", 0.0) or 0.0))

        while not self._stop_requested:
            window_start_mono = time.monotonic()
            window_start_wall = datetime.now()
            planned_calls = self._get_batch_size(config)
            planned_calls = max(1, int(planned_calls))

            operations_count = int(planned_calls * config.operations_weight / 100)
            guardrails_count = planned_calls - operations_count

            tasks: List[Dict[str, Any]] = []
            for _ in range(operations_count):
                agent = random.choice(self.agents)
                tasks.append({"type": "operation", "agent": agent})
            for _ in range(guardrails_count):
                agent = random.choice(self.agents)
                tasks.append({"type": "guardrail", "agent": agent})
            random.shuffle(tasks)

            target_rpm = (planned_calls / interval_s) * 60.0
            with self._metrics_lock:
                self._metrics.target_calls_per_minute = target_rpm
                self._metrics.current_load_profile = f"+/-{int(config.traffic_variance_pct)}%"
                self._metrics.batches_completed += 1
                self._metrics.last_batch_time = window_start_wall
                window_number = self._metrics.batches_completed
            self._update_queue_metrics()

            self._log(
                f"[SCHED] Window {window_number}: plan {operations_count} ops, {guardrails_count} guardrails "
                f"over {interval_s:.1f}s (target {target_rpm:.1f}/min) queue={self._task_queue.qsize() if self._task_queue else 0}"
            )
            self._update_metrics(self._metrics.to_dict())

            spacing_s = interval_s / planned_calls
            min_spacing_s = max(0.0, float(getattr(config, "delay", 0.0) or 0.0))
            spacing_s = max(spacing_s, min_spacing_s)
            for idx, task in enumerate(tasks):
                if self._stop_requested:
                    break
                scheduled_at = window_start_mono + (idx * spacing_s)
                if jitter_s:
                    scheduled_at += random.uniform(-jitter_s, jitter_s)
                while not self._stop_requested:
                    now = time.monotonic()
                    remaining = scheduled_at - now
                    if remaining <= 0:
                        break
                    time.sleep(min(0.05, remaining))
                ok = self._enqueue_task(task, config)
                if not ok and config.overload_policy != "block":
                    # Avoid per-call overload spam; one short hint per window is enough.
                    pass

            # Ensure window cadence; if we're behind, immediately start the next window.
            window_end = window_start_mono + interval_s
            while not self._stop_requested:
                now = time.monotonic()
                remaining = window_end - now
                if remaining <= 0:
                    break
                time.sleep(min(0.1, remaining))

        self._log("[SCHED] Scheduler stopped")

    def _worker_loop(self, worker_id: int, config: DaemonConfig) -> None:
        if not self._task_queue:
            return
        while True:
            if self._stop_requested and not config.drain_on_stop:
                break
            try:
                task = self._task_queue.get(timeout=0.2)
            except Empty:
                if self._stop_requested and not config.drain_on_stop:
                    break
                continue

            if self._stop_requested and not config.drain_on_stop:
                # Discard remaining queued tasks on stop (benchmark should stop quickly).
                try:
                    self._task_queue.task_done()
                except Exception:
                    pass
                continue

            with self._metrics_lock:
                self._metrics.started_calls += 1
                self._metrics.inflight_calls += 1
            self._update_queue_metrics()

            try:
                task_type = task.get("type")
                agent = task.get("agent")
                if task_type == "operation":
                    result_data = self._execute_operation(agent)
                    if result_data["result"] is not None:
                        self._process_operation_result(agent, result_data["result"])
                else:
                    result_data = self._execute_guardrail(agent)
                    if result_data["result"] is not None:
                        self._process_guardrail_result(
                            agent,
                            result_data["result"],
                            result_data.get("category"),
                            result_data.get("blocked", False),
                        )
            except Exception as exc:
                with self._metrics_lock:
                    self._metrics.failed_calls += 1
                    self._metrics.errors.append(str(exc)[:100])
                    self._metrics.errors = self._metrics.errors[-10:]
                self._log(f"[ERROR] Worker {worker_id} task failed: {exc}")
            finally:
                with self._metrics_lock:
                    self._metrics.inflight_calls = max(0, int(self._metrics.inflight_calls) - 1)
                self._update_queue_metrics()
                try:
                    self._task_queue.task_done()
                except Exception:
                    pass
                self._update_metrics(self._metrics.to_dict())

    def _daemon_loop(self, config: DaemonConfig) -> None:
        """Main daemon loop."""
        try:
            _ = create_openai_client()
            self._log("[DAEMON] Azure client factory initialized")

        except Exception as e:
            self._log(f"[ERROR] Failed to initialize Azure client: {e}")
            self._is_running = False
            return

        # Ensure output directory exists
        self._output_dir = config.output_dir
        os.makedirs(self._output_dir, exist_ok=True)
        self._start_metrics_flusher()
        self._maybe_flush_metrics(force=True)

        # Keep config accessible for logging behavior toggles.
        self._active_config = config
        # Normalize config fields that can be edited manually in JSON state.
        if getattr(config, "overload_policy", "drop") not in ("drop", "block"):
            config.overload_policy = "drop"
        config.log_sample_every = max(1, int(getattr(config, "log_sample_every", 1) or 1))
        config.latency_sample_size = max(10, int(getattr(config, "latency_sample_size", 1000) or 1000))
        with self._metrics_lock:
            self._metrics.latency_samples_ms = deque(self._metrics.latency_samples_ms, maxlen=config.latency_sample_size)

        queue_maxsize = self._resolve_queue_maxsize(config)
        self._task_queue = Queue(maxsize=queue_maxsize)
        self._workers = []

        # Start workers first so the scheduler can immediately enqueue.
        for idx in range(max(1, int(config.threads))):
            worker = threading.Thread(
                target=self._worker_loop,
                args=(idx, config),
                daemon=True,
                name=f"daemon-worker-{idx}",
            )
            worker.start()
            self._workers.append(worker)

        self._scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            args=(config,),
            daemon=True,
            name="daemon-scheduler",
        )
        self._scheduler_thread.start()

        self._log(
            f"[DAEMON] Non-blocking load generator started: interval={config.interval_seconds}s "
            f"calls=[{config.calls_per_batch_min},{config.calls_per_batch_max}] workers={len(self._workers)} "
            f"queue_maxsize={queue_maxsize} overload_policy={config.overload_policy}"
        )

        while not self._stop_requested:
            # Keep the main loop lightweight; the scheduler and workers do the work.
            time.sleep(0.2)

        self._is_running = False
        # Best-effort join so we stop promptly even if calls hang.
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            self._scheduler_thread.join(timeout=1.0)
        for worker in list(self._workers):
            if worker.is_alive():
                worker.join(timeout=0.5)
        self._maybe_flush_metrics(force=True)
        self._log("[DAEMON] Stopped")

    def _save_metrics(self, output_dir: str) -> None:
        """Save current metrics to file."""
        import json
        import tempfile
        metrics_file = os.path.join(output_dir, "daemon_metrics.json")
        history_file = os.path.join(output_dir, "daemon_history.jsonl")
        with self._metrics_lock:
            # Keep queue metrics fresh even if the UI only reads the metrics file.
            if self._task_queue is not None:
                self._metrics.queue_depth = int(self._task_queue.qsize() or 0)
            metrics_dict = self._metrics.to_dict()
            metrics_dict["saved_at"] = datetime.now().isoformat()
            metrics_dict["pid"] = os.getpid()
            metrics_dict["start_time"] = (
                self._metrics.start_time.isoformat() if self._metrics.start_time else None
            )
            metrics_dict["last_batch_time"] = (
                self._metrics.last_batch_time.isoformat() if self._metrics.last_batch_time else None
            )
            sample = {
                "timestamp": metrics_dict["saved_at"],
                "total_calls": self._metrics.total_calls,
                "total_operations": self._metrics.total_operations,
                "total_guardrails": self._metrics.total_guardrails,
            }
            self._metrics_history.append(sample)
            self._metrics_history = self._metrics_history[-self._metrics_history_max:]
            metrics_dict["history"] = list(self._metrics_history)

        os.makedirs(output_dir, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", delete=False, dir=output_dir) as tmp:
            json.dump(metrics_dict, tmp, indent=2)
            tmp.write("\n")
            temp_name = tmp.name
        os.replace(temp_name, metrics_file)

        # Append-only history for long-running runs (survives process restarts)
        try:
            with open(history_file, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(sample) + "\n")
        except Exception:
            # History is best-effort; daemon should not fail if the append can't happen.
            pass

    def _start_metrics_flusher(self) -> None:
        """Start a small heartbeat thread that flushes metrics even if calls are blocked."""
        if self._metrics_flusher_thread and self._metrics_flusher_thread.is_alive():
            return

        def flusher() -> None:
            while not self._stop_requested:
                self._maybe_flush_metrics(force=True)
                # Sleep in small steps so stop reacts quickly.
                for _ in range(int(self._metrics_flush_interval * 10)):
                    if self._stop_requested:
                        break
                    time.sleep(0.1)

        self._metrics_flusher_thread = threading.Thread(target=flusher, daemon=True)
        self._metrics_flusher_thread.start()

    def start(
        self,
        config: DaemonConfig,
        log_callback: Optional[Callable[[str], None]] = None,
        metrics_callback: Optional[Callable[[Dict], None]] = None,
    ) -> bool:
        """
        Start the daemon in a background thread.

        Args:
            config: Daemon configuration
            log_callback: Optional callback for log messages
            metrics_callback: Optional callback for metrics updates

        Returns:
            True if started successfully, False otherwise
        """
        if self._is_running:
            return False

        if not self.agents:
            return False

        self._log_callback = log_callback
        self._metrics_callback = metrics_callback
        self._stop_requested = False
        self._is_running = True

        # Reset metrics
        self._metrics = DaemonMetrics()
        self._metrics.start_time = datetime.now()
        self._metrics_history = []
        self._last_metrics_flush = 0.0

        self._daemon_thread = threading.Thread(
            target=self._daemon_loop,
            args=(config,),
            daemon=True,
        )
        self._daemon_thread.start()

        return True

    def run_blocking(
        self,
        config: DaemonConfig,
        log_callback: Optional[Callable[[str], None]] = None,
        metrics_callback: Optional[Callable[[Dict], None]] = None,
    ) -> None:
        """Run the daemon loop in the current thread."""
        if self._is_running:
            return

        if not self.agents:
            return

        self._log_callback = log_callback
        self._metrics_callback = metrics_callback
        self._stop_requested = False
        self._is_running = True
        self._metrics = DaemonMetrics()
        self._metrics.start_time = datetime.now()
        self._metrics_history = []
        self._last_metrics_flush = 0.0
        self._daemon_loop(config)

    def stop(self) -> None:
        """Stop the daemon."""
        self._stop_requested = True
        if self._daemon_thread and self._daemon_thread.is_alive():
            self._daemon_thread.join(timeout=5)
        if self._metrics_flusher_thread and self._metrics_flusher_thread.is_alive():
            self._metrics_flusher_thread.join(timeout=2)
        self._is_running = False

    def request_stop(self) -> None:
        """Request daemon shutdown without blocking."""
        self._stop_requested = True

    @property
    def is_running(self) -> bool:
        """Check if daemon is running."""
        return self._is_running

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics snapshot."""
        with self._metrics_lock:
            return self._metrics.to_dict()

    def get_agent_count(self) -> int:
        """Get number of loaded agents."""
        return len(self.agents)
