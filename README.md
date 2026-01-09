# Azure AI Foundry Control-Plane Batch Agent Operation

A comprehensive toolkit for batch creation, testing, and management of AI agents at scale using Azure AI Foundry Control Plane features. Supports industry-specific templates, parallel agent operations, and real-time metrics collection through intuitive Terminal and Web interfaces.

## Features

- **Batch Agent Operations**: Create and manage 100+ AI agents simultaneously with multi-threaded processing
- **Dual Interfaces**: Full-featured Terminal UI (Textual) and Web UI (Gradio) for interactive management
- **Industry Templates**: Pre-configured profiles for Retail, Financial Services, Healthcare, and Manufacturing with specialized agent types
- **Model Management**: Discover existing models and deploy new ones through Azure AI Foundry Control Plane
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
├── src/                  # Core library
│   ├── core/            # Business logic
│   │   ├── azure_client.py
│   │   ├── agent_manager.py
│   │   ├── model_manager.py
│   │   └── simulation_engine.py
│   ├── models/          # Pydantic models
│   ├── templates/       # Template utilities
│   └── codegen/         # Code generation
│
├── templates/            # Industry templates
│   ├── industries/      # YAML profiles
│   │   ├── retail.yaml
│   │   ├── financial_services.yaml
│   │   ├── healthcare.yaml
│   │   └── manufacturing.yaml
│   └── code/            # Jinja2 templates
│
└── ui/                   # User interfaces
    ├── terminal/        # Textual TUI
    ├── web/             # Gradio Web UI
    └── shared/          # Shared state
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

## License

[Your License Here]
