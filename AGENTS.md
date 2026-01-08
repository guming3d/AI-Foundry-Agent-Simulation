# Repository Guidelines

## Project Structure & Module Organization
- `foundry_demo/` holds the core package: agent generation, Azure operations, instructions/templates, and the entrypoints `tui.py` and `webui.py`.
- Root scripts power legacy workflows: `batch_create_agents.py`, `simulate_agent_operations.py`, `simulate_guardrail_testing.py`, `visualize_metrics.py`, and `test_simulation.py`.
- Templates live in `industry_templates/`; generated artifacts land in `workspaces/<timestamp>/` plus CSV/JSON/PNG outputs such as `created_agents_results.csv`, `simulation_metrics.csv`, and `metrics_visualization.png`.
- UI assets sit in `ui/`, and reference docs are in `README*.md`, `QUICKSTART.md`, and the guardrail guides.

## Build, Test, and Development Commands
- Environment: `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt` (Python 3.10+).
- Generator UIs: `python -m foundry_demo.tui` (Textual) or `python -m foundry_demo.webui` (Gradio).
- Create agents in Azure: `python batch_create_agents.py --csv workspaces/<ts>/agents_spec.csv` (requires `PROJECT_ENDPOINT` and `az login`).
- Simulate traffic: `python simulate_agent_operations.py --num-calls 100 --threads 5 --delay 0.5` → produces metrics and summary JSON.
- Guardrails and charts: `python simulate_guardrail_testing.py --input created_agents_results.csv` and `python visualize_metrics.py --input simulation_metrics.csv`.

## Coding Style & Naming Conventions
- Python-first with 4-space indents and type hints; prefer `pathlib.Path`, dataclasses, and small pure functions.
- snake_case for modules, variables, and file names; agent names follow `ORGXX-<Type>-AG###`.
- Keep comments minimal and focused on rationale; reuse shared helpers instead of duplicating script logic.

## Testing Guidelines
- Quick smoke: `python test_simulation.py` (5 calls) assumes `created_agents_results.csv` exists.
- For changes to generation or sims, run a small `simulate_agent_operations.py` sample before load tests and verify `simulation_metrics.csv` / `simulation_summary.json`.
- When adding guardrail cases, start with a limited agent subset in `simulate_guardrail_testing.py` and confirm results before scaling up.

## Commit & Pull Request Guidelines
- Commit subjects are imperative and ≤60 characters (e.g., `Add guardrail smoke test`); reference tickets with `Refs #123` when applicable.
- PRs should state why the change is needed, list commands executed (install, TUI/GUI runs, sims, guardrails), and note any impact on existing workspaces or agents.
- Keep `.env` local; only commit generated CSV/PNG artifacts when intentionally sharing outputs.

## Security & Configuration Tips
- Do not commit secrets or real endpoints; use `.env.example` plus env vars like `PROJECT_ENDPOINT`.
- Authenticate with `az login` or service principal env vars before running creation or simulation scripts.
- When updating templates or configs, keep a dated copy of the previous version and document model/endpoint assumptions in the PR notes.
