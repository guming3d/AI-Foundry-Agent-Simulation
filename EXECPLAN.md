# Add Sample Evaluations And Agent Application Flow

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

## Purpose / Big Picture

Users need a guided way to create and run multiple sample evaluations so they can learn how evaluation works with their agents. After this change, they can pick one or more sample evaluation templates, select agents, run the evaluations, and view a summary and saved JSON result file. They can access this flow from the terminal UI, and the evaluation templates live in a simple YAML directory they can open and study.

## Progress

- [x] (2025-02-14 12:10Z) Create evaluation templates and loader for sample evaluation definitions.
- [x] (2025-02-14 12:20Z) Implement evaluation engine to run templates against selected agents and persist results.
- [x] (2025-02-14 12:25Z) Wire evaluation state + results directory into shared config/state.
- [x] (2025-02-14 12:40Z) Add evaluation screen and navigation in the Textual TUI.
- [x] (2025-02-14 12:50Z) Add evaluation flow to the UI.
- [x] (2025-02-14 13:00Z) Validate with compile checks and document expected usage.
- [x] (2025-02-14 15:30Z) Switch evaluation runner to azure-ai-evaluation with project-backed model config.

## Surprises & Discoveries

- Observation: The installed Azure SDK does not expose the evaluation APIs used in `samples/evaluation`, so a local evaluation runner is required for working behavior.
  Evidence: `azure.ai.projects.AIProjectClient` has no `evaluations` attribute and no `evaluation` operations were found in the SDK package during inspection.
- Observation: The evaluation SDK requires Azure OpenAI model endpoint + key; the project deployment provides the backing connection name, so the engine must resolve connection credentials automatically.

## Decision Log

- Decision: Use the azure-ai-evaluation SDK (`evaluate`) for sample evaluations, deriving model config from the selected deployment’s project connection.
  Rationale: The new evaluation SDK is the supported path; it logs results to Foundry when given the project endpoint and removes the need for user-supplied model endpoint/key.
  Date/Author: 2025-02-14 / Codex

## Outcomes & Retrospective

Sample evaluation templates are available in `evaluation-templates/`, with an evaluation engine that builds datasets, calls agents, and runs evaluations through the azure-ai-evaluation SDK. The TUI exposes evaluation selection and execution, and results are saved under `results/evaluations/`. Model endpoint/key are resolved from the project deployment connection so users only select the evaluation model.

## Context and Orientation

This repository provides a CLI and Textual TUI for creating agents, running simulations, and viewing results. The TUI entry point is `ui/terminal/app.py`. Shared UI state is managed in `ui/shared/state_manager.py`. Core logic lives in `src/core/` and includes `simulation_engine.py` and `agent_manager.py` for agent operations and calling agents.

The new evaluation feature will be implemented in `src/core/` as a local evaluation engine. Sample evaluation templates will live in a new directory `evaluation-templates/` at the repository root, stored as YAML so users can open and study them. The evaluation engine will load templates, call selected agents via the existing OpenAI client flow, evaluate responses with simple heuristics (relevance overlap, basic BLEU-like precision, violence keyword scan, and string checks), and persist JSON results under `results/evaluations/`.

## Plan of Work

First, add `evaluation-templates/` with a few YAML templates that mirror the ideas from `samples/evaluation` (relevance + BLEU on a short QA dataset, a safety/violence scan, and a formatting/string check). Then implement `src/core/evaluation_templates.py` with dataclasses and a loader that reads those YAML files. Next, create `src/core/evaluation_engine.py` to run evaluations: it will accept template IDs and agent names, call agents through the OpenAI client, compute evaluator scores, build summaries, and write a JSON results file into a new `results/evaluations/` directory. Update `src/core/config.py` and `ui/shared/state_manager.py` to track evaluation results.

After the core is ready, add a new Textual screen `ui/terminal/screens/evaluation.py` that lets users select templates and agents, runs evaluations in a background thread, and shows progress and status. Wire it into `ui/terminal/app.py` and `ui/terminal/screens/home.py` for navigation.

Finish by running a compile check (`python -m compileall`) and summarizing usage in the README if needed.

## Concrete Steps

Run commands from the repository root `/home/minggu/projects_code/control-plane/generate-demo-data`.

1) Add evaluation templates under `evaluation-templates/` and implement the loader + engine in `src/core/`.
2) Update `src/core/config.py` and `ui/shared/state_manager.py` with evaluation result tracking.
3) Add the new Textual screen and navigation wiring.
4) Run a compile check:

    python -m compileall src ui

Expected output includes `compileall` success with no syntax errors.

## Validation and Acceptance

Start the TUI (`python main.py`), navigate to the Evaluations screen, select two sample evaluations and two agents, and run them. The status log should show progress and finish with a results file path under `results/evaluations/`.

Acceptance is met when users can create multiple evaluation runs in a single action and apply those evaluations to selected agents in the TUI.

## Idempotence and Recovery

Evaluation runs create new timestamped JSON files and do not mutate agents. Re-running is safe and will create new files. If a run fails, users can re-run after adjusting selections. No destructive steps are required.

## Artifacts and Notes

Expected result file path format:

    results/evaluations/basic-relevance_20250214T120000Z.json

The file contains per-agent evaluation summaries and raw responses.

## Interfaces and Dependencies

New modules and key interfaces:

- `src/core/evaluation_templates.py`
  - `EvaluationTemplateLoader.list_templates() -> list[EvaluationTemplate]`
  - `EvaluationTemplateLoader.load_template(template_id: str) -> EvaluationTemplate`
  - `EvaluationTemplate` dataclass with `id`, `display_name`, `description`, `dataset_items`, and `evaluators`.

- `src/core/evaluation_engine.py`
  - `EvaluationEngine.run(template_ids: list[str], agent_names: list[str], progress_callback: Optional[Callable]) -> list[dict]`
  - Uses `src/core/azure_client.get_openai_client` to call agents and returns summaries.

- `evaluation-templates/*.yaml`
  - YAML format with keys `id`, `display_name`, `description`, `dataset.items`, and `evaluators`.

These interfaces are used by `ui/terminal/screens/evaluation.py`.
