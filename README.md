# Microsoft Foundry Bootstrap

A comprehensive toolkit for batch creation, testing, and management of AI agents at scale using Microsoft Foundry Control Plane features. Supports industry-specific templates, parallel agent operations, and real-time metrics collection through an intuitive Terminal interface.

## Features

- **Batch Agent Operations**: Create and manage 100+ AI agents simultaneously with multi-threaded processing
- **Terminal Interface**: Full-featured Textual UI for interactive management
- **Industry Templates**: Pre-configured profiles for Retail, Financial Services, Healthcare, Manufacturing, Logistics & Transportation, Energy & Utilities, and Telecommunications with specialized agent types
- **Model Management**: Discover existing models and deploy new ones through Microsoft Foundry Control Plane
- **Code Generation**: Automatically generate production-ready simulation scripts from templates
- **Metrics & Visualization**: Real-time performance tracking with Plotly-powered dashboards
- **Agent Registry**: Centralized tracking of created agents with CSV-based persistence
- **Sample Evaluations**: Run reusable evaluation templates against selected agents using Foundry evaluation APIs

## Quick Start

```bash
# 1. Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Authenticate with Azure CLI (required for all operations)
az login
cp .env.example .env  # Edit with your PROJECT_ENDPOINT

# 4. Launch the toolkit
python main.py tui    # Terminal UI
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
│   │   ├── evaluation_engine.py
│   │   ├── evaluation_templates.py
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
├── evaluation-templates/ # Sample evaluation templates (YAML)
│
└── ui/                   # User interfaces
    ├── terminal/        # Textual TUI
    └── shared/          # Shared state
```

## CLI Commands

```bash
# Terminal UI
python main.py tui

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
| **logistics_transportation** | DispatchCoordinator, RouteOptimizer, FleetManager, ShipmentTracking |
| **energy_utilities** | GridDispatcher, OutageCoordinator, LoadForecaster, MarketOperations |
| **telecommunications** | NetworkMonitoring, IncidentManager, ProvisioningSpecialist, FraudPrevention |

## Environment Setup

Create `.env` from the example:

```env
PROJECT_ENDPOINT=https://your-project.services.ai.azure.com/api/projects/your-project
```

Authentication uses Azure CLI credentials via `DefaultAzureCredential`, so run `az login` before using the CLI or TUI.

## License

[Your License Here]
