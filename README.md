# Azure AI Foundry Control-Plane Batch Agent Operation

A comprehensive toolkit for batch creation, testing, and management of AI agents at scale using Azure AI Foundry Control Plane features. Supports industry-specific templates, parallel agent operations, continuous simulation, and real-time metrics collection through intuitive Terminal and Web interfaces.

## Features

- **Batch Agent Operations**: Create and manage 100+ AI agents simultaneously with multi-threaded processing
- **Dual Interfaces**: Full-featured Terminal UI (Textual) and Web UI (Gradio) for interactive management
- **Industry Templates**: Pre-configured profiles for Retail, Financial Services, Healthcare, and Manufacturing with specialized agent types
- **Continuous Simulation**: 24/7 daemon mode for sustained agent testing with configurable load profiles
- **Parallel Execution**: Thread-safe simulation engine supporting concurrent agent calls with real-time metrics
- **Model Management**: Discover existing models and deploy new ones through Azure AI Foundry Control Plane
- **Guardrail Testing**: Comprehensive security and compliance testing with automated attack simulations
- **Code Generation**: Automatically generate production-ready simulation scripts from templates
- **Metrics & Visualization**: Real-time performance tracking with Plotly-powered dashboards
- **Agent Registry**: Centralized tracking of created agents with CSV-based persistence

## Quick Start

```bash
# 1. Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure Azure credentials
az login
cp .env.example .env  # Edit with your PROJECT_ENDPOINT

# 4. Launch the toolkit
python main.py tui    # Terminal UI
python main.py web    # Web UI (opens browser)
```

## Project Structure

```
.
├── main.py                 # CLI entry point
├── requirements.txt        # Python dependencies
├── .env.example           # Environment template
│
├── config/                # Configuration files
│   ├── daemon_config.json
│   └── simulation-daemon.service
│
├── docs/                  # Documentation
│   ├── QUICKSTART.md
│   ├── SIMULATION.md
│   ├── DAEMON.md
│   └── GUARDRAIL_TESTING_GUIDE.md
│
├── scripts/               # Executable scripts
│   ├── agents/           # Agent management
│   │   ├── batch_create_agents.py
│   │   └── delete_all_agents.py
│   ├── simulation/       # Simulation runners
│   │   ├── simulate_operations.py
│   │   ├── simulate_guardrails.py
│   │   └── daemon.py
│   ├── visualization/    # Metrics visualization
│   │   ├── visualize_metrics.py
│   │   └── visualize_guardrails.py
│   └── utils/            # Utilities
│       └── test_azure_connection.py
│
├── examples/             # Example scripts
│   └── quickstart_create_agent.py
│
├── data/                 # Generated data (gitignored)
│   ├── agents/          # Agent registry
│   ├── results/         # Simulation results
│   └── daemon_results/  # Continuous simulation logs
│
├── src/                  # Core library
│   ├── core/            # Business logic
│   │   ├── azure_client.py
│   │   ├── agent_manager.py
│   │   ├── model_manager.py
│   │   └── simulation_engine.py
│   ├── models/          # Pydantic models
│   └── templates/       # Template utilities
│
├── templates/            # Industry templates
│   ├── industries/      # YAML profiles
│   │   ├── retail.yaml
│   │   ├── financial_services.yaml
│   │   ├── healthcare.yaml
│   │   └── manufacturing.yaml
│   └── code/            # Jinja2 templates
│
├── ui/                   # User interfaces
│   ├── terminal/        # Textual TUI
│   ├── web/             # Gradio Web UI
│   └── shared/          # Shared state
│
└── output/              # Generated code output
```

## CLI Commands

```bash
# Terminal UI
python main.py tui

# Web UI
python main.py web
python main.py web --port 8080 --share

# List templates
python main.py list

# Create agents
python main.py create retail -n 2 --orgs 3 -y

# Generate code
python main.py generate retail -o output/retail_code
```

## Industry Templates

| Industry | Agent Types |
|----------|-------------|
| **retail** | CustomerSupport, CatalogEnrichment, PricingOptimization, SupplyChain, MarketingCopy |
| **financial_services** | FraudDetection, RiskAssessment, ComplianceReview, CustomerService, PortfolioAnalysis |
| **healthcare** | PatientIntake, ClinicalDecisionSupport, BillingAssistant, AppointmentScheduler |
| **manufacturing** | QualityControl, PredictiveMaintenance, SupplyChainOptimizer, SafetyCompliance |

## Environment Setup

Create `.env` from the example:

```env
PROJECT_ENDPOINT=https://your-project.services.ai.azure.com/api/projects/your-project
```

## Documentation

- [Quick Start Guide](docs/QUICKSTART.md)
- [Simulation Guide](docs/SIMULATION.md)
- [Daemon (24/7 Operation)](docs/DAEMON.md)
- [Guardrail Testing](docs/GUARDRAIL_TESTING_GUIDE.md)
- [File Reference](docs/FILE_REFERENCE.md)

## License

[Your License Here]
