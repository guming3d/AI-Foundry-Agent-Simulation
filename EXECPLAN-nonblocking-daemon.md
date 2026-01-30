# Non-blocking load generator for simulation daemon

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This repository’s ExecPlans must be maintained in accordance with the ExecPlan requirements described in `~/.agent/PLANS.md`.

## Purpose / Big Picture

The long-running simulation daemon currently runs “batches” of calls and waits for every call in a batch to finish before scheduling the next batch. A single slow or stuck call can stall the entire benchmark, collapsing the observed calls/minute and making results unreliable.

After this change, the daemon becomes an open-loop, non-blocking load generator: each scheduling window (“batch window”) continues to enqueue calls at the configured target rate regardless of whether prior calls have completed. A bounded queue and explicit overload policy keep the daemon stable under overload while still accurately reporting how far the system is from the target rate.

Users can see it working by starting the daemon in the TUI and observing that “scheduled/started calls” continue to advance on each window even when some calls are slow, while completion rate and inflight counts reflect the system’s real capacity.

## Progress

- [x] (2026-01-25 18:35Z) Write design and acceptance criteria for non-blocking scheduling.
- [x] (2026-01-25 18:50Z) Implement queue-based scheduler and daemon worker pool.
- [x] (2026-01-25 19:05Z) Add inflight/overload/start-rate metrics and persist them in `daemon_metrics.json`.
- [x] (2026-01-25 19:10Z) Update the TUI to display the new benchmarking metrics.
- [x] (2026-01-25 19:15Z) Add unit tests for non-blocking behavior and overload handling; run `pytest`.

## Surprises & Discoveries

- Observation: “Non-blocking scheduling” and “achieving target throughput” are different. Even after removing per-batch waiting, completion throughput is still bounded by backend capacity and available concurrency, so the system must report target vs started vs completed distinctly.
  Evidence: The daemon now reports `target_calls_per_minute`, `started_calls_per_minute`, and `calls_per_minute` simultaneously in `daemon_metrics.json`.

## Decision Log

- Decision: Use a scheduler thread + daemon worker threads with a bounded queue (instead of per-batch `ThreadPoolExecutor` waiting on futures).
  Rationale: This makes scheduling independent from completion and avoids process shutdown being blocked by non-daemon executor threads when a request hangs.
  Date/Author: 2026-01-25 / Codex

- Decision: Treat the scheduling “batch window” as a time window, not a completion barrier, and keep the existing `batches_completed` metric as “windows scheduled” for backward-compatible UI behavior.
  Rationale: The UI already displays “Batches”; preserving the field avoids breaking dashboards while changing the underlying semantics to reflect non-blocking scheduling.
  Date/Author: 2026-01-25 / Codex

## Outcomes & Retrospective

The daemon load generator is now non-blocking across scheduling windows and behaves as a production benchmarking system with explicit backpressure visibility. Metrics now distinguish target rate, started rate, completion rate, inflight count, queue depth, dropped calls, and latency percentiles. The TUI displays these new metrics, and unit tests validate that slow calls do not prevent subsequent windows from scheduling and that overload drops are recorded.

## Context and Orientation

The long-running daemon code lives in `src/core/daemon_runner.py` and is launched out-of-process by `src/core/daemon_service.py`. The Textual UI screen that configures and starts the daemon is `ui/terminal/screens/simulation.py`.

In the current design, `DaemonRunner._daemon_loop` calls `_run_batch`, which submits a batch of tasks and then waits for all tasks in that batch to complete (`as_completed(futures)`), after which it sleeps `interval_seconds` and repeats. This creates “head-of-line blocking” where one slow call delays the next batch.

This plan replaces batch-waiting with a scheduler loop that enqueues calls across each interval while a separate pool of worker threads executes calls and records metrics.

Key terms used in this plan:

“Batch window” means a fixed-duration scheduling window of length `interval_seconds` during which the daemon attempts to start a configured number of calls.

“Open-loop load generator” means the daemon schedules calls according to time (the target rate), not according to completion of prior calls.

“Overload policy” means what the scheduler does when it cannot enqueue more work because the system is already saturated (drop new work, or block until capacity frees up).

## Plan of Work

First, extend `src/core/daemon_runner.py` configuration to include a bounded queue size and overload policy. Implement a scheduler thread that, each window, computes the planned number of calls, spreads them evenly across the window, and enqueues tasks without waiting for prior calls to finish.

Second, implement a daemon worker pool (daemon threads) that consumes tasks from the queue, performs the call, and updates metrics. The worker pool must be thread-safe for metrics and logging.

Third, extend `DaemonMetrics` to report both completion-based throughput (existing `calls_per_minute`) and scheduling/starting throughput. Add inflight counts, queue depth, and dropped counts so it behaves as a production benchmarking system with explicit backpressure visibility.

Fourth, update `ui/terminal/screens/simulation.py` to show the new metrics so users can interpret “target vs achieved”.

Finally, add unit tests under `tests/unit/` that stub out the call implementation so the scheduler can be verified deterministically. Tests must demonstrate that a slow call does not prevent subsequent windows from scheduling and that overload results in dropped enqueues with metrics reflecting that.

## Concrete Steps

Run commands from the repository root `/home/minggu/projects_code/control-plane/generate-demo-data`.

1) Implement the refactor and metrics changes:

    python -m compileall src ui

2) Run tests:

    pytest

## Validation and Acceptance

Acceptance is met when:

1) With a stubbed slow call (or under real slow calls), the daemon continues to schedule new work each interval without waiting for all in-flight calls to finish.

2) `daemon_results/daemon_metrics.json` contains:

    - A completion rate (`calls_per_minute`) that reflects completed calls.
    - A start/schedule rate (new field) that reflects requested load.
    - `inflight_calls`, `queue_depth`, and `dropped_calls` for backpressure visibility.

3) The TUI shows these new metrics and remains responsive.

## Idempotence and Recovery

Starting/stopping the daemon remains safe. The daemon continues to write metrics and history append-only. If overload occurs, the daemon must not crash; it should drop or delay work according to the configured policy and report that in metrics.

## Artifacts and Notes

(To be filled in during implementation with small transcripts and key metrics examples.)

## Interfaces and Dependencies

No new third-party dependencies are required. The refactor stays within `threading`, `queue`, and existing project utilities.

`src/core/daemon_runner.py` must end with:

- A daemon configuration that supports queue size and overload policy.
- A scheduler that is time-based and non-blocking with respect to call completion.
- A worker pool that can be stopped safely.
- Metrics that distinguish “scheduled/started” from “completed”.
