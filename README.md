# Azure AI Foundry Control Plane Demo Generator

This repo generates **agent fleets + simulation code** to demo Azure AI Foundry control-plane capabilities (agents, model deployments, usage metrics, and guardrail testing).

## What you can do

- Select **5–8 deployed model deployments** from your Foundry Project (or enter them manually)
- Pick an **industry profile** (YAML templates in `industry_templates/`, user-editable)
- Choose how many agents to generate; each agent gets a **random model** from your selection
- Generate runnable code:
  - `create_agents.py` (creates agents in your Foundry Project)
  - `simulate_agent_operations.py` (simulates realistic calls + writes metrics)
  - `simulate_guardrail_testing.py` (guardrail/security validation)
  - `simulation_daemon.py` + `daemon_manager.sh` (24/7 background simulation)
- Run the flow either via:
  - **Terminal TUI** (Textual)
  - **Web UI** (Gradio)

## Prerequisites

- Python 3.10+ recommended
- Azure auth configured (e.g., `az login`)
- `PROJECT_ENDPOINT` set (copy `.env.example` → `.env`)

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run (Terminal TUI)

```bash
python -m foundry_demo.tui
```

## Run (Web UI)

```bash
python -m foundry_demo.webui
```

## Outputs

Both UIs generate a workspace under `workspaces/<timestamp>/` containing:
- `agents_spec.csv` (the generated agent fleet)
- `create_agents.py` → produces `created_agents_results.csv`
- `simulate_agent_operations.py` → produces metrics + summary JSON
- `simulate_guardrail_testing.py` → produces guardrail results + report JSON
- Optional daemon scripts + config

## Notes on “model deployment”

The current `azure-ai-projects` SDK can **list** model deployments via `client.deployments.list()`, but does not (yet) expose a “create deployment” API. This app therefore:
- **selects from deployments already present** in your Foundry Project, and
- uses the selected deployment names when creating agents.

Deploy models using the Azure AI Foundry UI (or your org’s deployment pipeline), then select them in the app.

