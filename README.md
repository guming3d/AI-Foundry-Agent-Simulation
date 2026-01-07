# Azure AI Foundry Agent Creation & Demo Toolkit

A comprehensive toolkit for creating, testing, and demonstrating AI agents using Azure AI Foundry Control Plane features. Provides dual interfaces (Terminal UI and Web UI) with industry-specific templates and automated code generation.

## Table of Contents

- [Features](#features)
- [Architecture Overview](#architecture-overview)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Usage Guide](#usage-guide)
  - [Terminal UI (TUI)](#terminal-ui-tui)
  - [Web UI](#web-ui)
  - [CLI Commands](#cli-commands)
- [Industry Templates](#industry-templates)
- [Component Reference](#component-reference)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)

---

## Features

- **Dual Interfaces**: Full-featured Terminal UI (Textual) and Web UI (Gradio)
- **Industry Templates**: Pre-configured profiles for Retail, Financial Services, Healthcare, and Manufacturing
- **Agent Management**: Create, list, and manage AI agents in Azure AI Foundry
- **Model Management**: Discover existing models and deploy new ones
- **Code Generation**: Automatically generate simulation scripts from templates
- **Simulation Engine**: Run operations and guardrail tests with real-time metrics
- **Results Dashboard**: Interactive charts and exportable data

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER INTERFACES                                 │
├─────────────────────────────────┬───────────────────────────────────────────┤
│      Terminal UI (Textual)      │           Web UI (Gradio)                 │
│  ┌───────────────────────────┐  │  ┌─────────────────────────────────────┐  │
│  │ F1: Home                  │  │  │ Tab 1: Models                       │  │
│  │ F2: Model Selection       │  │  │ Tab 2: Industry Profiles            │  │
│  │ F3: Industry Profiles     │  │  │ Tab 3: Agent Creation               │  │
│  │ F4: Agent Wizard          │  │  │ Tab 4: Simulation                   │  │
│  │ F5: Simulation            │  │  │ Tab 5: Results                      │  │
│  │ F6: Results               │  │  │                                     │  │
│  └───────────────────────────┘  │  └─────────────────────────────────────┘  │
└─────────────────────────────────┴───────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SHARED STATE MANAGER                               │
│                      (ui/shared/state_manager.py)                           │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ • Current Profile    • Selected Models    • Created Agents          │    │
│  │ • Simulation Results • Generated Code Path • Operation Summary      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CORE ENGINE                                     │
├──────────────────┬──────────────────┬──────────────────┬────────────────────┤
│   Agent Manager  │  Model Manager   │ Simulation Engine│  Metrics Collector │
│                  │                  │                  │                    │
│ • Create agents  │ • List models    │ • Run operations │ • Thread-safe      │
│ • List agents    │ • Deploy models  │ • Run guardrails │ • CSV/JSON export  │
│ • Delete agents  │ • Validate       │ • Progress track │ • Aggregation      │
│ • CSV export     │                  │                  │                    │
└──────────────────┴──────────────────┴──────────────────┴────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           TEMPLATE SYSTEM                                    │
├─────────────────────────────────────┬───────────────────────────────────────┤
│         Template Loader             │          Code Generator               │
│   (YAML → Pydantic Models)          │      (Jinja2 Templates)               │
│                                     │                                       │
│  templates/industries/              │  templates/code/                      │
│  ├── retail.yaml                    │  ├── simulate_operations.py.j2        │
│  ├── financial_services.yaml        │  ├── simulate_guardrails.py.j2        │
│  ├── healthcare.yaml                │  └── daemon_config.json.j2            │
│  └── manufacturing.yaml             │                                       │
└─────────────────────────────────────┴───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AZURE AI FOUNDRY                                     │
│                                                                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐  │
│  │  AI Project     │  │  Model          │  │  Content Safety             │  │
│  │  Client         │  │  Deployments    │  │  Guardrails                 │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Select     │     │   Create     │     │   Generate   │     │     Run      │
│   Profile    │ ──▶ │   Agents     │ ──▶ │    Code      │ ──▶ │  Simulation  │
│   (YAML)     │     │   (Azure)    │     │   (Jinja2)   │     │   (Metrics)  │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
       │                    │                    │                    │
       ▼                    ▼                    ▼                    ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Industry     │     │ agents.csv   │     │ operations.py│     │ metrics.csv  │
│ Profile      │     │              │     │ guardrails.py│     │ summary.json │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
```

---

## Quick Start

```bash
# 1. Clone and setup
git clone <repository-url>
cd AI-Foundry-Agent-Simulation

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure Azure credentials
az login
cp .env.example .env  # Edit with your PROJECT_ENDPOINT

# 5. Launch the toolkit
python main.py tui    # Terminal UI
# or
python main.py web    # Web UI (opens browser)
```

---

## Installation

### Prerequisites

- Python 3.8+
- Azure CLI (`az`) installed and configured
- Azure AI Foundry project with endpoint access

### Dependencies

```bash
pip install -r requirements.txt
```

Key packages:
| Package | Purpose |
|---------|---------|
| `azure-ai-projects` | Azure AI Foundry SDK |
| `azure-identity` | Azure authentication |
| `textual` | Terminal UI framework |
| `gradio` | Web UI framework |
| `pydantic` | Data validation |
| `jinja2` | Code templating |
| `pyyaml` | YAML parsing |
| `plotly` | Interactive charts |

### Environment Setup

Create a `.env` file in the project root:

```env
PROJECT_ENDPOINT=https://your-project.services.ai.azure.com/api/projects/your-project
```

---

## Usage Guide

### Terminal UI (TUI)

Launch the terminal-based interface:

```bash
python main.py tui
```

**Navigation:**
| Key | Screen | Description |
|-----|--------|-------------|
| F1 | Home | Welcome screen with quick actions |
| F2 | Models | Browse and deploy AI models |
| F3 | Profiles | Select industry templates |
| F4 | Agents | Create agents wizard |
| F5 | Simulation | Run operations/guardrails |
| F6 | Results | View metrics and charts |
| Q | - | Quit application |

**Workflow Example:**
1. Press `F3` to select an industry profile (e.g., "retail")
2. Press `F2` to select models for your agents
3. Press `F4` to create agents (set org count, agents per type)
4. Press `F5` to run simulation
5. Press `F6` to view results

### Web UI

Launch the Gradio web interface:

```bash
python main.py web                    # Default port 7860
python main.py web --port 8080        # Custom port
python main.py web --share            # Create public URL
```

Open your browser to `http://localhost:7860`

**Tabs:**
1. **Models** - List available models, deploy new ones
2. **Industry Profiles** - Browse templates, view YAML
3. **Agent Creation** - Configure and create agents
4. **Simulation** - Run tests with live progress
5. **Results** - Interactive Plotly charts, data tables

### CLI Commands

For scripting and automation:

```bash
# List available industry templates
python main.py list

# Create agents from a template
python main.py create retail -n 2 --orgs 3 -y
#   -n, --count    Agents per type (default: 1)
#   --orgs         Number of organizations (default: 1)
#   -o, --output   Output CSV path
#   -y, --yes      Skip confirmation prompt

# Generate simulation code
python main.py generate retail -o output/retail_code
#   -o, --output      Output directory
#   --agents-csv      Path to agents CSV

# Full help
python main.py --help
python main.py create --help
```

---

## Industry Templates

Four pre-configured templates are included:

### Retail / E-commerce
```bash
python main.py create retail
```
| Agent Type | Department | Use Case |
|------------|------------|----------|
| CustomerSupport | CX | Order tracking, returns |
| CatalogEnrichment | Catalog | Product descriptions |
| PricingOptimization | Pricing | Dynamic pricing |
| SupplyChain | Operations | Inventory management |
| MarketingCopy | Marketing | Campaign content |

### Financial Services
```bash
python main.py create financial_services
```
| Agent Type | Department | Use Case |
|------------|------------|----------|
| FraudDetection | Risk | Transaction monitoring |
| RiskAssessment | Risk | Credit evaluation |
| ComplianceReview | Compliance | Regulatory checks |
| CustomerService | CX | Account support |
| PortfolioAnalysis | Wealth | Investment advice |

### Healthcare
```bash
python main.py create healthcare
```
| Agent Type | Department | Use Case |
|------------|------------|----------|
| PatientIntake | Clinical | Registration |
| ClinicalDecisionSupport | Clinical | Diagnosis assistance |
| BillingAssistant | Billing | Claims processing |
| AppointmentScheduler | Admin | Scheduling |
| MedicalRecordsSummary | IT | Record summarization |

### Manufacturing
```bash
python main.py create manufacturing
```
| Agent Type | Department | Use Case |
|------------|------------|----------|
| QualityControl | QA | Defect detection |
| PredictiveMaintenance | Maintenance | Equipment monitoring |
| SupplyChainOptimizer | Supply | Logistics |
| SafetyCompliance | Safety | OSHA compliance |
| ProductionScheduler | Production | Scheduling |

### Custom Templates

Create your own template at `templates/industries/custom.yaml`:

```yaml
metadata:
  id: custom
  name: "My Custom Industry"
  version: "1.0.0"
  description: "Custom agent configuration"

organization:
  prefix: "CUSTOM"
  departments:
    - name: "Department Name"
      code: "DEPT"

models:
  preferred:
    - "gpt-4.1-mini"
  allowed:
    - "gpt-4.1-mini"
    - "gpt-5.2-chat"

agent_types:
  - id: "MyAgent"
    name: "My Custom Agent"
    department: "DEPT"
    instructions: |
      You are a specialized AI agent for...
    query_templates:
      - "Template query with placeholder {}"

guardrail_tests:
  harms_content:
    - "Test harmful query"
  jailbreak_content:
    - "Test jailbreak query"
```

---

## Component Reference

### Core Modules

| Module | Path | Description |
|--------|------|-------------|
| Azure Client | `src/core/azure_client.py` | Singleton factory for Azure SDK clients |
| Agent Manager | `src/core/agent_manager.py` | Agent CRUD operations |
| Model Manager | `src/core/model_manager.py` | Model discovery and deployment |
| Simulation Engine | `src/core/simulation_engine.py` | Run operations and guardrails |
| Metrics Collector | `src/core/metrics_collector.py` | Thread-safe metrics aggregation |

### Data Models

| Model | Path | Description |
|-------|------|-------------|
| Agent | `src/models/agent.py` | Agent data structures |
| IndustryProfile | `src/models/industry_profile.py` | Profile configuration |
| SimulationConfig | `src/models/simulation_config.py` | Simulation settings |

### Template System

| Component | Path | Description |
|-----------|------|-------------|
| Template Loader | `src/templates/template_loader.py` | YAML parsing with validation |
| Template Renderer | `src/templates/template_renderer.py` | Jinja2 code generation |
| Code Generator | `src/codegen/generator.py` | Orchestrates code generation |

### User Interfaces

| UI | Path | Description |
|----|------|-------------|
| TUI App | `ui/terminal/app.py` | Textual main application |
| TUI Screens | `ui/terminal/screens/` | 6 TUI screen modules |
| Web App | `ui/web/app.py` | Gradio main application |
| Web Tabs | `ui/web/tabs/` | 5 Gradio tab modules |
| State Manager | `ui/shared/state_manager.py` | Shared application state |

---

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `PROJECT_ENDPOINT` | Yes | Azure AI Foundry project endpoint |
| `AZURE_CLIENT_ID` | No | Service principal client ID |
| `AZURE_CLIENT_SECRET` | No | Service principal secret |
| `AZURE_TENANT_ID` | No | Azure AD tenant ID |

### Simulation Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `num_calls` | 50 | Number of API calls per simulation |
| `threads` | 3-5 | Parallel worker threads |
| `delay` | 0.5s | Delay between calls (rate limiting) |

---

## Troubleshooting

### Authentication Issues

```
Error: DefaultAzureCredential failed to retrieve a token
```

**Solution:**
```bash
az login
az account set --subscription "Your-Subscription"
```

### Module Not Found

```
ModuleNotFoundError: No module named 'textual'
```

**Solution:**
```bash
pip install -r requirements.txt
```

### Template Not Found

```
Error: Template 'custom' not found
```

**Solution:** Ensure your YAML file is in `templates/industries/` with correct `metadata.id`.

### Rate Limiting (429 Errors)

**Solution:** Increase delay or reduce threads:
```bash
# In simulation settings:
delay: 2.0
threads: 2
```

---

## License

[Your License Here]

## Contributing

[Contribution guidelines]

## Support

For issues and feature requests, please open an issue on GitHub.
